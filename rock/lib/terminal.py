import re
import curses
import asyncio
import codecs
import threading

fp = open('log.log', 'w+')

ESCAPE_SEQUENCE_RE = re.compile(r'''
  ( \\U........      # 8-digit hex escapes
  | \\u....          # 4-digit hex escapes
  | \\x..            # 2-digit hex escapes
  | \\[0-7]{1,3}     # Octal escapes
  | \\N\{[^}]+\}     # Unicode characters by name
  | \\[\\'"abfnrtv]  # Single-character escapes
  )''', re.UNICODE | re.VERBOSE)

COMMANDS = [
  [re.compile(r'\x1B\[([0-9]+)A'), '[UP:\g<1>]'],
  [re.compile(r'\x1B\[2K'), '[DELETE]'],
  [re.compile(r'\x1B\[1B'), '[ESCAPE]'],
  [re.compile(r'\x1B\[2B'), ''],
  [re.compile(r'\r'), '']
]

ACTION = re.compile(r'(\[[A-Z]+(?::[0-9]+)?\])')

COMMAND = re.compile(r'\[([A-Z]+):?([0-9]+)?\]')

class Terminal:
  def __init__(self):
    self.current_y = 0
    self.max_y = 1
    self.output_h = 0

  def __del__(self):
    self.stop()

  def start(self, heading=None):
    self.screen = curses.initscr()
    self.setup()
    if heading:
      self.header(heading)

  def stop(self):
    curses.echo()
    curses.nocbreak()
    curses.curs_set(1)
    curses.endwin()

  async def listen(self):
    while True:
      c = self.screen.getch()

      if c == curses.KEY_UP:
        if self.current_y > 0: self.current_y -= 1
        self.refresh()
      elif c == curses.KEY_DOWN:
        if self.current_y < self.max_y-self.output_h: self.current_y += 1
        self.refresh()
      elif c == ord('q') or c == ord('Q') or c == KeyboardInterrupt:
        break
      await asyncio.sleep(0.01)
    
    self.stop()

  def setup(self):
    curses.curs_set(1)
    curses.noecho()
    curses.cbreak()

    self.screen.nodelay(1)
    self.screen.keypad(True)

    if curses.has_colors():
      curses.start_color()
      curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
      curses.init_pair(2, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
      curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
      curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
      curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)
      curses.init_pair(6, curses.COLOR_RED, curses.COLOR_BLACK)

    self.colors = { '___0___': 0 }
    self.current_color = 1
    self.output_h = curses.LINES-3
    self.current_y = -self.output_h+1
    self.output_w = curses.newwin(curses.LINES-2, curses.COLS, 1, 0)
    self.output_p = curses.newpad(curses.LINES-4, curses.COLS-2)
    self.output_w.box()
    self.output_p.scrollok(True)
    self.output_p.idlok(1)
    self.refresh()

  def header(self, text):
    self.screen.addstr(0, 0, ' %s' % text, curses.A_REVERSE)
    self.screen.chgat(-1, curses.A_REVERSE)
    self.refresh()

  def write(self, text, color=0):
    actions = list(filter(None, re.split(ACTION, self.decode(text))))

    line_break = True

    for action in actions:
      match = COMMAND.match(action)
      if match is not None and hasattr(self, match.group(1).lower()):
        if match.group(2) is not None:
          getattr(self, match.group(1).lower())(match.group(2))
        else:
          getattr(self, match.group(1).lower())()
      else:
        components = self.color(action)
        for component in components:
          #if not component['text'].endswith('\n'):
          #  component['text'] = '%s\n' % component['text']
          fp.write(component['text'])

          self.output_p.addstr(component['text'], curses.color_pair(component['color']))
          self.current_y  += 1
          self.max_y      += 1
          self.refresh()

  def refresh(self):
    self.output_p.resize(self.max_y+1, curses.COLS-2)
    self.screen.refresh()
    self.output_w.refresh()
    #self.output_p.refresh(self.current_y-1, 0, 2, 0, curses.LINES-2, curses.COLS)
    self.output_p.refresh(self.current_y, 0, 2, 1, self.output_h, curses.COLS-2)

  def delete(self):
    fp.write('Deleted line\n')
    self.origin()
    self.output_p.clrtoeol()
    self.refresh()

  def escape(self):
    y, x = self.output_p.getyx()
    while True:
      try:
        y += 1
        self.output_p.move(y, 0)
        fp.write('Escaped down\n')
      except:
        break
    self.refresh()

  def origin(self):
    y, x = self.output_p.getyx()
    self.output_p.move(y, 0)
    self.refresh()

  def up(self, lines):
    y, x = self.output_p.getyx()
    for i in range(y, y-int(lines) if y-int(lines) >= 0 else 0, -1):
      fp.write('Moved up\n')
      self.output_p.move(i, x)
    self.refresh()

  def down(self):
    self.max_y += 1
    self.output_p.resize(self.max_y, curses.COLS)
    y, x = self.output_p.getyx()
    self.output_p.move(y+1, x)
    self.refresh()

  def color(self, text):
    text = self.decode(text)
    ansi_escape = re.compile(r'\x9B|\x1B\[([0-9]*)[ -\/]*[@-~]')
    color_escape = re.compile(r'(___[0-9]+___)')
    color_match = re.compile(r'___([0-9]+)___')
    text = ansi_escape.sub(r'___\1___', text)
    parts = color_escape.split(text)
    components = [{ 'text': parts[0], 'color': 0 }]

    for i in range(1, len(parts), 2):
      match = color_escape.match(parts[i])
      if match:
        if not match.group(1) in self.colors:
          self.colors[match.group(1)] = self.current_color

          # We only have 6 colors to work with. After we reach the limit, all remaining new colors will be the same
          if self.current_color < 6:
            self.current_color += 1

        components.append({ 'text': parts[i+1], 'color': self.colors[match.group(1)] })
        i += 1
      else:
        components.append({ 'text': parts[i], 'color': 0 })

    return components

  def decode(self, text):
    try:
      text = text.decode('utf-8')
    except:
      pass
    def decode_match(match):
      return codecs.decode(match.group(0), 'unicode-escape')
    for cmd in COMMANDS:
      text = cmd[0].sub(cmd[1], text)
    return ESCAPE_SEQUENCE_RE.sub(decode_match, text)
