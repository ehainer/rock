import re
import curses
import asyncio
import codecs
import threading

import time

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
  [re.compile(r'\x1B\[([0-9]+)B'), '[DOWN:\g<1>]'],
  [re.compile(r'\x1B\[2K'), '[DELETE]'],
  [re.compile(r'\r'), '']
]

ACTION = re.compile(r'(\[[A-Z]+(?::[0-9]+)?\])')

COMMAND = re.compile(r'\[([A-Z]+):?([0-9]+)?\]')

class Terminal:
  def __init__(self):
    self.current_y = 0
    self.max_y = 0
    self.output_h = 0
    self.line = 0
    self.lines = []
    self.listener = threading.Thread(target=self.listen)

  def __del__(self):
    self.stop()

  def start(self):
    self.screen = curses.initscr()
    self.setup()
    self.listener.start()

  def stop(self):
    self.listener.join()
    self.listener.stop()
    curses.echo()
    curses.nocbreak()
    curses.curs_set(1)
    curses.endwin()

  def listen(self):
    while True:
      c = self.screen.getch()

      if c == curses.KEY_UP:
        if self.current_y > 0: self.current_y -= 1
        if self.current_y < 0: self.current_y = 0
        self.refresh(False)
      elif c == curses.KEY_DOWN:
        if self.current_y < self.max_y-self.output_h: self.current_y += 1
        if self.current_y > self.max_y-self.output_h: self.current_y = self.max_y-self.output_h
        self.refresh(False)
      elif c == curses.KEY_PPAGE:
        if self.current_y > 0: self.current_y -= self.output_h
        if self.current_y < 0: self.current_y = 0
        self.refresh(False)
      elif c == curses.KEY_NPAGE:
        if self.current_y < self.max_y-self.output_h: self.current_y += self.output_h
        if self.current_y > self.max_y-self.output_h: self.current_y = self.max_y-self.output_h
        self.refresh(False)
      elif c == ord('q') or c == ord('Q') or c == KeyboardInterrupt:
        break
      time.sleep(0.01)
    
    raise KeyboardInterrupt

  def setup(self):
    curses.curs_set(0)
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
    self.output_h = curses.LINES-2
    self.output_w = curses.newwin(curses.LINES-1, curses.COLS, 1, 0)
    self.output_p = curses.newpad(curses.LINES-2, curses.COLS)
    self.output_p.idlok(1)
    self.refresh()

  def header(self, text):
    self.screen.addstr(0, 0, ' %s' % text, curses.A_REVERSE)
    self.screen.chgat(-1, curses.A_REVERSE)
    self.refresh()

  def write(self, text, fcolor=None):
    actions = list(filter(None, re.split(ACTION, self.decode(text))))

    for action in actions:
      match = COMMAND.match(action)
      if match is not None and hasattr(self, match.group(1).lower()):
        if match.group(2) is not None:
          getattr(self, match.group(1).lower())(match.group(2))
        else:
          getattr(self, match.group(1).lower())()
      else:
        components = self.color(action)
        for text, color in components:
          # Allow overriding of color if any found in ANSI codes
          if fcolor is not None: color = fcolor

          # Add the lines to the list, increment current "line" by 1
          self.lines.insert(self.line, (text, color))
          self.line += 1

          # If at the bottom of the window, keep scrolling with any new output
          if self.current_y == self.max_y-self.output_h: self.current_y += 1

    self.refresh()

  def refresh(self, redraw=True):
    if redraw:
      self.output_p.clear()
      self.max_y = 0
      for text, color in self.lines:
        if text:
          self.max_y += text.count('\n')
          self.output_p.resize(self.max_y+1, curses.COLS)
          try:
            self.output_p.addstr(text, curses.color_pair(color))
          except:
            pass

    self.screen.noutrefresh()
    self.output_w.noutrefresh()
    self.output_p.noutrefresh(self.current_y, 0, 1, 0, self.output_h, curses.COLS)
    curses.doupdate()

  def delete(self):
    self.lines[self.line] = ('\n', 0)

  def escape(self):
    self.line = len(self.lines)

  def up(self, lines):
    self.line -= int(lines)

  def down(self, lines):
    self.line += int(lines)

  def color(self, text):
    text = self.decode(text)
    ansi_escape = re.compile(r'\x9B|\x1B\[([0-9]*)[ -\/]*[@-~]')
    color_escape = re.compile(r'(___[0-9]+___)')
    color_match = re.compile(r'___([0-9]+)___')
    text = ansi_escape.sub(r'___\1___', text)
    parts = color_escape.split(text)
    components = [(parts[0], 0)]

    for i in range(1, len(parts), 2):
      match = color_escape.match(parts[i])
      if match:
        if not match.group(1) in self.colors:
          self.colors[match.group(1)] = self.current_color

          # We only have 6 colors to work with. After we reach the limit, all remaining new colors will be the same
          if self.current_color < 6:
            self.current_color += 1

        components.append((parts[i+1], self.colors[match.group(1)]))
        i += 1
      else:
        components.append((parts[i], 0))

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
