from rock.lib.terminal import Terminal
from rock.lib.machine import Machine
from contextlib import suppress
from rock.lib.terminal import COLOR_BLUE, COLOR_YELLOW, COLOR_CYAN, COLOR_MAGENTA, COLOR_GREEN, COLOR_RED

import io
import os
import sys
import curses
import asyncio
import signal
import codecs
import subprocess
import docker
import concurrent.futures
import traceback
import threading

import time

class Run:
  def __init__(self):
    self.docker_task = None
    self.docker_up = None
    self.docker_down = None
    self.machine = Machine()
    self.stopper = threading.Event()
    self.terminal = curses.wrapper(Terminal, self.stopper)
    self.loop = asyncio.get_event_loop()
    self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    try:
      self.terminal.start()
      self.loop.run_until_complete(self.start_machine())
      self.loop.run_until_complete(self.start_docker())
      self.loop.create_task(self.watch())
      self.loop.run_forever()
    #except Exception as ex:
    #  self.loop.stop()
    #  self.terminal.stop()
    #  traceback.print_exc()
    #  print(ex)
    except KeyboardInterrupt:
      self.terminal.write('^CGracefully stopping... (Press Ctrl+C again to force)')
      self.terminal.bottom()
      time.sleep(3)
      self.terminal.stop()
      for task in asyncio.Task.all_tasks():
        print(task)
      self.stopper.set()
      self.loop.close()
      self.loop.stop()
      #self.docker_up.terminate()
      #self.loop.run_until_complete(self.stop_docker())
    #finally:
    #  self.terminal.stop()
    #  self.loop.stop()
    #  self.loop.close()

  async def watch(self):
    futures = []
    label_w = 0

    futures.append(self.loop.run_in_executor(self.executor, self.terminal.listen, self.stopper))

    for label, container in self.machine.containers():
      if len(label) > label_w: label_w = len(label)
      futures.append(self.loop.run_in_executor(self.executor, self.output, label, container, self.stopper))

    self.terminal.label_width = label_w
    await asyncio.gather(*futures)

  async def start_docker(self):
    return await asyncio.create_subprocess_shell('docker-compose up -d', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env=self.env())

  async def stop_docker(self):
    return await asyncio.create_subprocess_shell('docker-compose down', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env=self.env(False))

  def output(self, label, container, stopper):
    for line in container.logs(stream=True, follow=True):
      if stopper.is_set(): break
      self.terminal.write(line, label=label)

  async def start_machine(self):
    if not self.machine.running():
      self.terminal.write('Starting machine "%s" ... ' % self.machine.name(), end='')
      result = self.machine.start()
      if result:
        self.terminal.write('OK', color=COLOR_GREEN, end='\n\n')
        self.terminal.header('Running %s @ %s' % (self.machine.project(), self.machine.ip()))
        return True
      else:
        self.terminal.write('Failed', color=COLOR_RED, end='\n\n')
        return False
    else:
      self.terminal.write('Machine "%s" already started ... ' % self.machine.name(), end='')
      self.terminal.write('OK', color=COLOR_GREEN, end='\n\n')
      self.terminal.header('Running %s @ %s' % (self.machine.project(), self.machine.ip()))
      return True

  def env(self, output=True):
    docker_env = os.environ.copy()
    for k, v in self.machine.config().items():
      docker_env[k] = v
      if output:
        self.terminal.write('Set env ', end='')
        self.terminal.write(k, color=COLOR_YELLOW, end='')
        self.terminal.write(' ... %s' % v)
    if output: self.terminal.write('\n')
    return docker_env
