from rock.lib.terminal import Terminal
from rock.lib.machine import Machine
from contextlib import suppress

import io
import os
import sys
import curses
import asyncio
import signal
import codecs
import subprocess

import time

class Run:
  def __init__(self):
    self.docker_task = None
    self.docker_up = None
    self.docker_down = None
    self.machine = Machine()
    self.terminal = curses.wrapper(Terminal)
    self.loop = asyncio.get_event_loop()

    try:
      self.terminal.start()
      self.loop.run_until_complete(self.start_machine())
      self.loop.create_task(self.start_docker())
      self.loop.run_forever()
    except Exception as ex:
      print(ex)
    except asyncio.CancelledError:
      pass
    except KeyboardInterrupt:
      self.terminal.write('\n^C Gracefully stopping docker. Press Ctrl+C again to kill\n')
      self.terminal.bottom()
      self.docker_up.terminate()
      self.loop.run_until_complete(self.stop_docker())
      self.terminal.stopper.set()
    finally:
      self.terminal.stop()
      self.loop.stop()
      self.loop.close()

  async def start_docker(self):
    # , preexec_fn=os.setpgrp
    self.docker_up = await asyncio.create_subprocess_shell('docker-compose up', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env=self.env())
    await asyncio.wait([
      self.output(self.docker_up.stdout)
    ])
    return await self.docker_up.wait()

  async def stop_docker(self):
    self.docker_down = await asyncio.create_subprocess_shell('docker-compose down', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env=self.env(False))
    await asyncio.wait([
      self.output(self.docker_down.stdout)
    ])
    return await self.docker_down.wait()

  async def output(self, stream):
    empty = 0
    while True:
      try:
        line = await asyncio.wait_for(stream.readline(), 0.1)
      except asyncio.TimeoutError:
        pass
      else:
        if line == b'': empty += 1
        if empty > 2000: break
        self.terminal.write(line)

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

  def decode(self, text):
    def decode_match(match):
      return codecs.decode(match.group(0), 'unicode-escape')
    try:
      for cmd in COMMANDS:
        text = cmd[0].sub(cmd[1], text)
      return ESCAPE_SEQUENCE_RE.sub(decode_match, str(text, 'utf-8'))
    except:
      return str(text)

  def env(self, output=True):
    docker_env = os.environ.copy()
    for k, v in self.machine.config():
      docker_env[k] = v
      if output:
        self.terminal.write('Set env ')
        self.terminal.write(k, 2)
        self.terminal.write(' ... %s\n' % v)
    if output: self.terminal.write('\n')
    return docker_env
