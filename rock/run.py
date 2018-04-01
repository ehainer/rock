from __future__ import print_function

from dotenv import load_dotenv, dotenv_values
from machine import Machine

import io
import re
import curses
import os
import sys
import time
import copy
#import subprocess
import asyncio
import codecs

max_y = 0
y = 0
log_h = 0
loop = asyncio.get_event_loop()
colors = {}
current_color = 1
a = 0

ESCAPE_SEQUENCE_RE = re.compile(r'''
  ( \\U........      # 8-digit hex escapes
  | \\u....          # 4-digit hex escapes
  | \\x..            # 2-digit hex escapes
  | \\[0-7]{1,3}     # Octal escapes
  | \\N\{[^}]+\}     # Unicode characters by name
  | \\[\\'"abfnrtv]  # Single-character escapes
  )''', re.UNICODE | re.VERBOSE)

#sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

class Run:
  def __init__(self, arg_input):
    global args
    global y
    global max_y
    global log_h
    global loop
    args = arg_input
    self.start()

    stdscr = curses.initscr()

    buff = io.StringIO()
    window_y = 2
    window_b = curses.LINES-1
    window_h = curses.LINES-window_y
    current_y = 0

    stdscr.keypad(True)

    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)

    if curses.has_colors():
      curses.start_color()

    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)

    stdscr.addstr(0, 0, ' Running @ ' + Machine().ip(self.machine_name()), curses.A_REVERSE)
    stdscr.chgat(-1, curses.A_REVERSE)

    log_window = curses.newwin(curses.LINES-2, curses.COLS, 2, 0)

    log_pad = curses.newpad(curses.LINES-2, curses.COLS)
    log_pad.scrollok(True)
    log_pad.idlok(1)

    log_h = curses.LINES-3

    loop = asyncio.get_event_loop()
    loop.run_until_complete(self.run_stream(
      'docker-compose up',
      curses,
      stdscr,
      log_window,
      log_pad
    ))
    loop.close()

    while True:
      c = stdscr.getch()

      if c == curses.KEY_UP:
        if y > log_h: y -= 1
        log_pad.refresh(y-log_h, 0, 2, 0, curses.LINES-2, curses.COLS)
      elif c == curses.KEY_DOWN:
        if y < max_y: y += 1
        log_pad.refresh(y-log_h, 0, 2, 0, curses.LINES-2, curses.COLS)

      if c == ord('q') or c == ord('Q'):
        break
    
    buff.close()
    self.restoreScreen()

  #def __del__(self):
  #  print('\n')
  #  self.restoreScreen()

  def restoreScreen(self):
    curses.echo()
    curses.nocbreak()
    curses.curs_set(1)
    curses.endwin()

  async def write_line(self, curses, stdscr, log_window, log_pad, components):
    global y
    global max_y
    global log_h
    for i in range(0, len(components)):
      log_pad.resize(max_y+components[i]['word'].count('\n'), curses.COLS)
      log_pad.addstr(str(components[i]['color']) + ' ::: ' + components[i]['word'], curses.color_pair(int(components[i]['color'])))
      y     += components[i]['word'].count('\n')
      max_y += components[i]['word'].count('\n')
      stdscr.refresh()
      log_window.refresh()
      log_pad.refresh(y-log_h, 0, 2, 0, curses.LINES-2, curses.COLS)

  async def read_stream(self, stream, curses, stdscr, log_window, log_pad):
    global a
    global ESCAPE_SEQUENCE_RE
    global colors
    global current_color
    while True:
      line = await stream.readline()
      if line:
        a += 1
        line = self.decode_escapes(str(line, 'utf-8'))

        ansi_escape = re.compile(r'\x9B|\x1B\[([0-9]*)[ -\/]*[@-~]')
        color_escape = re.compile(r'(___[0-9]+___)')
        color_match = re.compile(r'___([0-9]+)___')
        line = ansi_escape.sub(r'___\1___', line)
        parts = color_escape.split(line)
        components = []

        for i in range(0, len(parts)):
          color = '0'
          match = color_escape.match(parts[i])
          if match:
            if not match.group(1) in colors:
              colors[match.group(1)] = current_color
              color = str(current_color)
              current_color += 1
            components = components[:]
            components.append({ 'word': parts[i+1], 'color': color })
          else:
            components = components[:]
            components.append({ 'word': parts[i], 'color': color })

        if a >= 20:
          self.restoreScreen()
          print(colors)
          print(current_color)
          print(components)
          exit(1)
        await self.write_line(curses, stdscr, log_window, log_pad, components)
      else:
        break

  async def run_stream(self, cmd, curses, stdscr, log_window, log_pad):
    process = await asyncio.create_subprocess_shell(cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)

    await asyncio.wait([
        self.read_stream(process.stdout, curses, stdscr, log_window, log_pad)
    ])
    return await process.wait()

  def running(self):
    return Machine().status(self.machine_name())

  def stop(self):
    return Machine().stop(self.machine_name())

  def start(self):
    if not self.running():
      print('Starting Machine "%(name)s" ... ' % { 'name': self.machine_name() }, end='')
      result = Machine().start(self.machine_name())
      if result:
        print('OK')
      else:
        print('Failed')
    else:
      print('Machine "%(name)s" already started ... OK' % { 'name': self.machine_name() })
      return True

  def machine_name(self):
    env = io.StringIO()
    env.write(self.load_file('.env'))
    env.seek(0)
    parsed = dotenv_values(stream=env)
    return parsed['DOCKER_MACHINE']

  def load_file(self, path):
    with open(path, 'r') as file:
      return file.read()

  def decode_escapes(self, s):
    def decode_match(match):
      return codecs.decode(match.group(0), 'unicode-escape')

    return ESCAPE_SEQUENCE_RE.sub(decode_match, s)