from __future__ import print_function

from dotenv import load_dotenv, dotenv_values
from machine import Machine

import io
import curses
import os
import sys
import time
#import subprocess
import asyncio
import codecs

max_y = 0
y = 0
log_h = 0
loop = asyncio.get_event_loop()

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

  def write_line(self, curses, stdscr, log_window, log_pad, line):
    global y
    global max_y
    global log_h
    log_pad.resize(max_y+line.count('\n'), curses.COLS)
    log_pad.addstr(r'%s' % line)
    y     += line.count('\n')
    max_y += line.count('\n')
    stdscr.refresh()
    log_window.refresh()
    log_pad.refresh(y-log_h, 0, 2, 0, curses.LINES-2, curses.COLS)

  async def read_stream(self, stream, curses, stdscr, log_window, log_pad):
    while True:
      line = await stream.readline()
      if line:
        line = str(line, 'utf-8')
        ansi_foreground = curses.tigetstr('setaf')
        if(ansi_foreground):
          line = curses.tparm(ansi_foreground, 1)
        self.write_line(curses, stdscr, log_window, log_pad, line)
      else:
        break

  async def run_stream(self, cmd, curses, stdscr, log_window, log_pad):
    # ^[[33mpostgres_1  |^[[0m
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
