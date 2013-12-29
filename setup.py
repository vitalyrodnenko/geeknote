from setuptools import setup, find_packages
import sys, os

version = '0.0.1'

setup(name='geeknote',
      version=version,
      description="GeekNote python evernote client",
      long_description="""\
      a python evernote client
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='evernote',
      author='Vitaliy Rodenko',
      author_email='contact@geeknote.me',
      url='http://geeknote.me',
      license='MIT',
      packages=find_packages(),
      include_package_data=True,
      entry_points={
          'console_scripts': [ 'geeknote = geeknote:main' ] 
      },
      )
