from rock.lib.terminal import Terminal
from rock.lib.machine import Machine

import io
import os
import sys
import curses
import time
import asyncio
import threading
import signal
import codecs

import re

class Run:
  def __init__(self, arg_input):
    global args
    args = arg_input

    self.process = None
    self.machine = Machine()
    self.terminal = Terminal()
    self.terminal.start('Running %s @ %s' % (self.machine.project(), self.machine.ip()))

    #threading.Thread(target=self.terminal.start, args=('Running %s @ %s' % (self.machine.project(), self.machine.ip()),)).start()

    # self.start()

    self.loop = asyncio.get_event_loop()
    #try:
      #self.loop.run_until_complete(self.start())
      #self.loop.run_until_complete(self.configure())
      #self.loop.run_until_complete(self.run())

    self.loop.run_until_complete(self.start_all())
    #except (Exception, KeyboardInterrupt):
      #if self.process:
      #  self.process.send_signal(signal.SIGINT)
      #self.terminal.stop()
    #self.loop.run_until_complete(self.write_stuff())
    time.sleep(5)
    #self.loop.close()

  async def start_all(self):
    await asyncio.wait([
      self.run(),
      self.terminal.listen()
    ])

  async def run(self):
    self.process = await asyncio.create_subprocess_shell('docker-compose up', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)

    await asyncio.wait([
        self.read_stream(self.process.stdout)
    ])
    return await self.process.wait()

  async def write_stuff(self):
    #for i in range(0, 100):
    #  self.terminal.write('\nHello World %s' % i, 2)

    #await asyncio.sleep(5)
    for i in range(1, 81):
      self.terminal.write('Line %s\n' % i, 2)
      await asyncio.sleep(0.01)
    #await asyncio.sleep(5)
    #self.terminal.up(2)
    #self.terminal.delete()
    #await asyncio.sleep(1)
    #self.terminal.write(b'\x1b[2A\x1b[2K\rStarting landwise_redis_1    ... done\r\x1b[1A\x1b[2K\rStarting landwise_postgres_1 ... done\r\x1b[1BStarting landwise_rails_1    ... \r\n')
    #await asyncio.sleep(1)
    #self.terminal.write(b'\x1b[1A\x1b[2K\rStarting landwise_rails_1    ... done\r\x1b[1BAttaching to landwise_redis_1, landwise_postgres_1, landwise_rails_1\n')
    #await asyncio.sleep(1)
    
    #self.terminal.write('Starting landwise_redis_1 ... done\n')
    #self.terminal.write(b'\x1b[2A\x1b[2K\rStarting landwise_redis_1    ... \x1b[32mdone\x1b[0m\r\x1b[2B\x1b[1A\x1b[2K\rStarting landwise_postgres_1 ... \x1b[32mdone\x1b[0m\r\x1b[1BStarting landwise_rails_1    ... \r\n')

  async def read_stream(self, stream):
    while True:
      line = await stream.readline()
      if line:
        #print('%s' % line)
        self.terminal.write(line)
      else:
        break

  async def start(self):
    if not self.machine.running():
      self.terminal.write('\nStarting machine "%s" ... ' % self.machine.name())
      result = self.machine.start()
      if result:
        self.terminal.write('OK', 5)
        return True
      else:
        self.terminal.write('Failed', 6)
        return False
    else:
      self.terminal.write('\nMachine "%s" already started ... ' % self.machine.name())
      self.terminal.write('OK', 5)
      return True

  async def configure(self):
    for k, v in self.machine.config():
      self.terminal.write('\nSet env ')
      self.terminal.write(k, 4)
      self.terminal.write(' ... %s' % v)

  def decode(self, text):
    def decode_match(match):
      return codecs.decode(match.group(0), 'unicode-escape')
    try:
      for cmd in COMMANDS:
        text = cmd[0].sub(cmd[1], text)
      return ESCAPE_SEQUENCE_RE.sub(decode_match, str(text, 'utf-8'))
    except:
      return str(text)