import os
import io
import sys
from ruamel.yaml import YAML
from string import Template

class Create:
  def __init__(self, arg_input):
    global args
    args = arg_input
    if self.check_services():
      self.machine()
      self.project()
      self.build()
    else:
      exit(1)

  def check_services(self):
    valid = True
    for service in args.services:
      if not os.path.exists('rock/services/' + service.lower() + '.yml'):
        print('File rock/services/' + service.lower() + '.yml not found and can not be added as a service.')
        valid = False
    return valid

  def build(self):
    self.write_compose()
    self.write_dockerfile()
    self.write_environment()

  def write_compose(self):
    print('Writing docker-compose.yml ... ', end='')
    yaml = YAML()
    compose = yaml.load(self.load_file('rock/templates/docker-compose.yml'))
    compose['services'] = {}

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

      #if 'version' in srv:
      #  ver = input('%s version to use (%s)' % (srv['version']))

      if 'volumes' in srv:
        if not 'volumes' in compose:
          compose['volumes'] = {}
        for i in srv['volumes']:
          compose['volumes'].update({ i: srv['volumes'][i] })

    yaml.preserve_quotes = True
    yaml.boolean_representation = ['False', 'True']
    yaml.indent(sequence=4, offset=2)
    with open('docker-compose.yml', 'w') as fp:
      yaml.dump(compose, fp)
    print('Done')

  def write_dockerfile(self):
    print('Writing Dockerfile ... ', end='')
    template = Template(self.load_file('rock/templates/Dockerfile')).safe_substitute(vars(args))
    with open('Dockerfile', 'w') as dockerfile:
      dockerfile.write(template)
    print('Done')

  def write_environment(self):
    print('Writing .env ... ', end='')
    template = Template(self.load_file('rock/templates/.env')).safe_substitute({ 'MACHINE': self.machine(), 'PROJECT': self.project() })
    environment = open('.env', 'w')
    with open('.env', 'w') as env:
      env.write(template)
    print('Done')
    
  def load_file(self, path):
    with open(path, 'r') as file:
      return file.read()

  def machine(self):
    global machine_name
    if not 'machine_name' in globals():
      machine_name = args.machine
    if machine_name == None:
      machine_name = input('Machine Name: ')
    return machine_name

  def project(self):
    global project_name
    if not 'project_name' in globals():
      project_name = args.project
    if project_name == None:
      project_name = input('Project Name: ')
    return project_name