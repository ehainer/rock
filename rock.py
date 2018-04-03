#!/usr/bin/env python3.5

import os
import sys
import argparse
from rock.add import Add
from rock.run import Run
from rock.clean import Clean
from rock.create import Create
from rock.execute import Execute
from rock.install import Install

class Rock:
  def __init__(self):
    parser = argparse.ArgumentParser(
      description='Manage rails docker containers',
      usage='''rock <command> [<args>]'''
    )
    parser.add_argument('command')
    args = parser.parse_args(sys.argv[1:2])
    if not hasattr(self, args.command):
        print('Unrecognized command: ', args.command)
        parser.print_help()
        exit(1)
    getattr(self, args.command)()

  def create(self):
    parser = argparse.ArgumentParser(
      description='Create new docker project config',
      usage='''rock create [service, service, ...]'''
    )
    parser.add_argument('-p', '--project', help='Project name, to namespace containers')
    parser.add_argument('-m', '--machine', help='Docker machine name under which to run the project')
    parser.add_argument('-r', '--ruby', help='Ruby version', default='2.5.0')
    parser.add_argument('services', nargs='*', help='List of services to include as containers')
    args = parser.parse_args(sys.argv[2:])
    Create(args)

  def add(self):
    parser = argparse.ArgumentParser(
      description='Add services to existing docker config',
      usage='''rock add [service, service, ...]'''
    )
    parser.add_argument('services', nargs='*', help='List of services to add as containers')
    args = parser.parse_args(sys.argv[2:])
    Add(args)

  def clean(self):
    parser = argparse.ArgumentParser(
      description='Remove all containers, volumes, and images associated with the current project',
      usage='''rock clean'''
    )
    args = parser.parse_args(sys.argv[2:])
    Clean()

  def run(self):
    parser = argparse.ArgumentParser(
      description='Run the current docker project',
      usage='''rock run'''
    )
    args = parser.parse_args(sys.argv[2:])
    Run()

  def install(self):
    parser = argparse.ArgumentParser(
      description='Install docker and related docker dependencies',
      usage='''rock install'''
    )
    args = parser.parse_args(sys.argv[2:])
    Install()

#def clean():
#  name = getenv('COMPOSE_PROJECT_NAME')
#  confirm = raw_input('Are you sure you want to delete all ' + name + ' containers? This cannot be undone (Y/n): ')
#  if confirm == 'Y':
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
#
#def exe():
#  name = getenv('COMPOSE_PROJECT_NAME')
#  process = subprocess.call('docker-compose run rails ' + ' '.join(args.services), shell=True)
#  #for line in iter(process.stdout.readline, ''):
#  #  sys.stdout.write(line)

if __name__ == '__main__':
  Rock()
