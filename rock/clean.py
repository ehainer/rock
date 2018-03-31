from __future__ import print_function

from ruamel.yaml import YAML
from string import Template
from dotenv import load_dotenv

import os
import sys
import docker

class Clean:
  def __init__(self):
    self.remove_images()

  def remove_images(self):
    client = docker.from_env()

    try:
      results = client.images.prune()
      print('Images Removed: {}'.format(results['ImagesDeleted']))
      print('Space Recovered: {}'.format(self.sizeof_fmt(results['SpaceReclaimed'])))
    except docker.errors.APIError:
      print('API Error encountered while removing images')
      exit(1)

  def sizeof_fmt(self, num, suffix='B'):
    for unit in ['', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB']:
      if abs(num) < 1024.0:
        return "%3.1f%s%s" % (num, unit, suffix)
      num /= 1024.0
    return "%.1f%s %s" % (num, 'Yi', suffix)


#    process = Popen('docker stop $(docker ps -a -q -f name=' + name + ')', stdout=PIPE, shell=True)
#    for line in iter(process.stdout.readline, ''):
#      sys.stdout.write('Stopping container: ' + line)
#
#    process = Popen('docker rm $(docker ps -a -q -f name=' + name + ')', stdout=PIPE, shell=True)
#    for line in iter(process.stdout.readline, ''):
#      sys.stdout.write('Removing container: ' + line)
#
#    process = Popen('docker rmi -f $(docker images | awk \'$1 ~ /' + name + '/ { print $3 }\')', stdout=PIPE, shell=True)
#    for line in iter(process.stdout.readline, ''):
#      sys.stdout.write('Removing image: ' + line)
#
#    process = Popen('docker volume prune -f', stdout=PIPE, shell=True)
#    for line in iter(process.stdout.readline, ''):
#      sys.stdout.write('Removing volume: ' + line)