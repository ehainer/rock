from __future__ import print_function

import os
import sys
from ruamel.yaml import YAML
from string import Template

class Add:
  def __init__(self, arg_input):
    global args
    args = arg_input
    if self.check_services():
      self.inject()
    else:
      exit(1)

  def check_services(self):
    valid = True
    for service in args.services:
      if not os.path.exists('rock/services/' + service.lower() + '.yml'):
        print('File rock/services/' + service.lower() + '.yml not found and can not be added as a service.')
        valid = False
    return valid

  def inject(self):
    print('Updating docker-compose.yml ... ', end='')
    yaml = YAML()
    compose = yaml.load(file('docker-compose.yml'))

    for service in args.services:
      srv = yaml.load(self.load_file('rock/services/' + service + '.yml'))

      for i in srv['services']:
        compose['services'].update({ i: srv['services'][i] })

      if 'dependency_of' in srv:
        for dependency in srv['dependency_of']:
          if not 'depends_on' in compose['services'][dependency]:
            compose['services'][dependency].update({ 'depends_on': [service] })
          else:
            compose['services'][dependency]['depends_on'].append(service)

      if 'volumes' in srv:
        if not 'volumes' in compose:
          compose['volumes'] = {}
        for i in srv['volumes']:
          compose['volumes'].update({ i: srv['volumes'][i] })

    yaml.preserve_quotes = True
    yaml.boolean_representation = ['False', 'True']
    yaml.indent(sequence=4, offset=2)
    yaml.dump(compose, file('docker-compose.yml', 'w'))
    print('Done')

  def load_file(self, path):
    with open(path, 'r') as file:
      return file.read()