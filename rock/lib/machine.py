from machine import Machine as Docker
from dotenv import dotenv_values

import io
import re
import docker

DOCKER_ENVS = re.compile(r'(DOCKER_[A-Z_]+)="(.+?)"\n')

class Machine:
  def __init__(self):
    env = io.StringIO()
    env.write(self.load_file('.env'))
    env.seek(0)
    self.env = dotenv_values(stream=env)
    self.docker_client = None

  def running(self):
    return Docker().status(self.name())

  def config(self):
    env = '\n'.join(Docker().env(self.name()))
    return { str(match.group(1)) : str(match.group(2)) for match in DOCKER_ENVS.finditer(env) }

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

  def containers(self):
    for container in self.client().containers.list(filters={ 'name': self.project() }):
      label = container.name.replace('%s_' % self.project(), '')
      yield label, container

  def client(self):
    try:
      return docker.from_env(environment=self.config())
    except requests.exceptions.ConnectionError as e:
      raise RockError(str(e))

  def load_file(self, path):
    with open(path, 'r') as file:
      return file.read()