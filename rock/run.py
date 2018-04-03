from rock.lib.terminal import Terminal
from rock.lib.machine import Machine

import io
import os
import sys
import curses
import asyncio
import signal
import codecs

class Run:
  def __init__(self):
    self.docker_up = None
    self.docker_down = None
    self.machine = Machine()
    self.terminal = Terminal()

    self.terminal.start()

    self.loop = asyncio.get_event_loop()
    try:
      self.loop.run_until_complete(self.start_machine())
      self.loop.run_until_complete(self.configure())
      self.loop.run_until_complete(self.start_docker())
    #except asyncio.CancelledError:
    #  pass
    except KeyboardInterrupt:
      for task in asyncio.Task.all_tasks():
        task.cancel()
      self.docker_up.send_signal(signal.SIGINT)
      self.loop.stop()
    finally:
      #self.loop.run_until_complete(self.stop_docker())
      self.terminal.stop()
    self.loop.close()
    exit(0)

  async def start_docker(self):
    await asyncio.wait([
      self.run()
    ])

  async def stop_docker(self):
    self.docker_down = await asyncio.create_subprocess_shell('docker-compose down', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)

    await asyncio.wait([
        self.read_stream(self.docker_down.stdout)
    ])
    return await self.docker_down.wait()

  async def run(self):
    self.docker_up = await asyncio.create_subprocess_shell('docker-compose up', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, preexec_fn=os.setpgrp)

    await asyncio.wait([
        self.read_stream(self.docker_up.stdout)
    ])
    return await self.docker_up.wait()

  async def read_stream(self, stream):
    while True:
      line = await stream.readline()
      if line:
        self.terminal.write(line)
      else:
        break

  async def start_machine(self):
    if not self.machine.running():
      self.terminal.write('Starting machine "%s" ... ' % self.machine.name())
      result = self.machine.start()
      if result:
        self.terminal.write('OK\n\n', 5)
        self.terminal.header('Running %s @ %s' % (self.machine.project(), self.machine.ip()))
        return True
      else:
        self.terminal.write('Failed\n\n', 6)
        return False
    else:
      self.terminal.write('Machine "%s" already started ... ' % self.machine.name())
      self.terminal.write('OK\n\n', 5)
      self.terminal.header('Running %s @ %s' % (self.machine.project(), self.machine.ip()))
      return True

  async def configure(self):
    for k, v in self.machine.config():
      self.terminal.write('Set env ')
      self.terminal.write(k, 4)
      self.terminal.write(' ... %s\n' % v)
    self.terminal.write('\n')

  def decode(self, text):
    def decode_match(match):
      return codecs.decode(match.group(0), 'unicode-escape')
    try:
      for cmd in COMMANDS:
        text = cmd[0].sub(cmd[1], text)
      return ESCAPE_SEQUENCE_RE.sub(decode_match, str(text, 'utf-8'))
    except:
      return str(text)