#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Import python libs
import os
import sys
import shutil
from setuptools import setup, Command

NAME = 'virt'
DESC = ('')

# Version info -- read without importing
_locals = {}
with open('{}/version.py'.format(NAME)) as fp:
    exec(fp.read(), None, _locals)
VERSION = _locals['version']
SETUP_DIRNAME = os.path.dirname(__file__)
if not SETUP_DIRNAME:
    SETUP_DIRNAME = os.getcwd()

with open('README.rst', encoding='utf-8') as f:
    LONG_DESC = f.read()

with open('requirements-test.txt') as f:
    TEST_REQUIREMENTS = f.read().splitlines()

with open('requirements.txt') as f:
    REQUIREMENTS = f.read().splitlines()

class Clean(Command):
    user_options = []
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for subdir in (NAME, 'tests'):
            for root, dirs, files in os.walk(os.path.join(os.path.dirname(__file__), subdir)):
                for dir_ in dirs:
                    if dir_ == '__pycache__':
                        shutil.rmtree(os.path.join(root, dir_))


def discover_packages():
    modules = []
    for package in (NAME, ):
        for root, _, files in os.walk(os.path.join(SETUP_DIRNAME, package)):
            pdir = os.path.relpath(root, SETUP_DIRNAME)
            modname = pdir.replace(os.sep, '.')
            modules.append(modname)
    return modules


setup(name=NAME,
      author='',
      author_email='',
      url='',
      version=VERSION,
      install_requires=REQUIREMENTS,
      tests_require=TEST_REQUIREMENTS,
      description=DESC,
      long_description=LONG_DESC,
      long_description_content_type='text/x-rst',
      python_requires='>=3.6',
      classifiers=[
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Development Status :: 5 - Production/Stable',
          ],
      entry_points={
        'console_scripts': [
            'virt = virt.scripts:start',
            ],
          },
      packages=discover_packages(),
      cmdclass={'clean': Clean},
      )
