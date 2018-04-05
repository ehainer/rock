from machine import Machine as Docker
from dotenv import dotenv_values

import io
import re

DOCKER_ENVS = re.compile(r'(DOCKER_[A-Z_]+)="(.+?)"\n')

class Machine:
  def __init__(self):
    env = io.StringIO()
    env.write(self.load_file('.env'))
    env.seek(0)
    self.env = dotenv_values(stream=env)

  def running(self):
    return Docker().status(self.name())

  def config(self):
    env = '\n'.join(Docker().env(self.name()))
    for match in DOCKER_ENVS.finditer(env):
      yield str(match.group(1)), str(match.group(2))
    return True

  def ip(self):
    return Docker().ip(self.name())

  def start(self):
    return Docker().start(self.name())

  def stop(self):
    return Docker().stop(self.name())

  def name(self):
    return self.env['DOCKER_MACHINE']

  def project(self):
    return self.env['COMPOSE_PROJECT_NAME']

  def load_file(self, path):
    with open(path, 'r') as file:
      return file.read()