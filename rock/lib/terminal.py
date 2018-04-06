import re
import curses
import asyncio
import codecs
import threading
import traceback

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

COLOR_BLUE = (1, curses.COLOR_BLUE)
COLOR_YELLOW = (2, curses.COLOR_YELLOW)
COLOR_CYAN = (3, curses.COLOR_CYAN)
COLOR_MAGENTA = (4, curses.COLOR_MAGENTA)
COLOR_GREEN = (5, curses.COLOR_GREEN)
COLOR_RED = (6, curses.COLOR_RED)

COLORS = [COLOR_BLUE, COLOR_YELLOW, COLOR_CYAN, COLOR_MAGENTA, COLOR_GREEN, COLOR_RED]

class Terminal:
  def __init__(self, stdscr, stopper):
    self.screen = stdscr
    self.label_width = 0
    self.current_y = 0
    self.max_y = 1
    self.output_h = 0
    self.colors = {}
    self.current_color = 1
    self.screen.resize(1, curses.COLS)

  def __del__(self):
    self.stop()

  def start(self):
    self.setup()

  def stop(self):
    curses.nl()
    curses.echo()
    curses.nocbreak()
    curses.curs_set(1)
    curses.endwin()

  def listen(self, stopper):
    while True and not stopper.is_set():
      c = self.screen.getch()

      if c == curses.KEY_UP:
        if self.current_y > 0: self.current_y -= 1
        self.refresh()
      elif c == curses.KEY_DOWN:
        if self.current_y < self.max_y-self.output_h: self.current_y += 1
        self.refresh()
      elif c == curses.KEY_PPAGE:
        if self.current_y > 0: self.current_y -= self.output_h
        self.refresh()
      elif c == curses.KEY_NPAGE:
        if self.current_y < self.max_y-self.output_h: self.current_y += self.output_h
        self.refresh()
      elif c == ord('q') or c == ord('Q'):
        break
      time.sleep(0.01)

  def setup(self):
    curses.curs_set(0)
    curses.noecho()
    curses.cbreak()
    curses.nl()

    self.screen.nodelay(1)
    self.screen.keypad(True)

    if curses.has_colors():
      curses.start_color()
      for index, color in COLORS:
        curses.init_pair(index, color, curses.COLOR_BLACK)

    self.output_h = curses.LINES-1
    self.output_p = curses.newpad(self.output_h, curses.COLS)
    self.output_p.scrollok(True)
    self.output_p.idlok(1)
    self.refresh()

  def header(self, text):
    self.screen.addstr(0, 0, ' %s' % text, curses.A_REVERSE)
    self.screen.chgat(-1, curses.A_REVERSE)
    self.refresh()

  def write(self, text, color=(0,0), label=None, end='\n'):
    text = self.decode(text).strip('\n')
    self.max_y += text.count('\n')+1
    self.refresh()

    # Add the label, if any, then text, then the end line character
    self.output_p.addstr(*self.label(label))
    self.output_p.addstr(*self.line(text, color=color))
    self.output_p.addstr(end)

    self.refresh()

  def refresh(self):
    # Resize the pad to make room for text
    self.output_p.resize(self.max_y, curses.COLS)

    # If at the bottom of the window, remain at the bottom of the window when more text is added
    if self.current_y == self.max_y-self.output_h: self.current_y += 1

    # Ensure we are scrolling somewhere within the scrollable area
    if self.current_y < 0: self.current_y = 0
    if self.current_y > self.max_y-self.output_h: self.current_y = self.max_y-self.output_h

    # Refresh the contents of the window, scrolling to current scroll position
    self.screen.noutrefresh()
    self.output_p.noutrefresh(self.current_y, 0, 1, 0, self.output_h, curses.COLS)
    curses.doupdate()

  def label(self, text=None):
    if text is not None:
      color = self.colorize(text)
      left = '%s | ' % text.ljust(self.label_width)
      return left, curses.color_pair(color)
    return '', curses.color_pair(0)

  def line(self, text, color=(0,0)):
    return text, curses.color_pair(color[0])

  def top(self):
    self.current_y = 0

  def bottom(self):
    self.current_y = self.max_y-self.output_h
    self.refresh()

#  def delete(self):
#    self.lines[self.line] = ('\n', 0)
#
#  def escape(self):
#    self.line = len(self.lines)
#
#  def up(self, lines):
#    self.line -= int(lines)
#
#  def down(self, lines):
#    self.line += int(lines)

  def colorize(self, text):
    if text not in self.colors:
      self.colors[text] = self.current_color
      if self.current_color < 6:
        self.current_color += 1
    return self.colors[text]

  def decode(self, text):
    try:
      text = text.decode('utf-8')
    except:
      pass
    def decode_match(match):
      return codecs.decode(match.group(0), 'unicode-escape')
    return ESCAPE_SEQUENCE_RE.sub(decode_match, text)
