#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement
import sys
import os
from setuptools import setup
from setuptools.command.install import install


BASH_COMPLETION = '''
_geeknote_command()
{
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"

    SAVE_IFS=$IFS
    IFS=" "
    args="${COMP_WORDS[*]:1}"
    IFS=$SAVE_IFS

    COMPREPLY=( $(compgen -W "`geeknote autocomplete ${args}`" -- ${cur}) )

    return 0
}
complete -F _geeknote_command geeknote
'''


class full_install(install):

    user_options = install.user_options + [
        ('userhome', None, "(Linux only) Set user home directory for"
                           " bash completion (/home/{0})".format(os.getlogin()))
    ]

    def initialize_options(self):
        install.initialize_options(self)
        self.userhome = ''

    def run(self):
        if sys.platform == 'linux2':
            self.install_autocomplite()
        install.run(self)

    def install_autocomplite(self):
        if self.userhome:
            self.userhome = '{0}/.bash_completion'.format(self.userhome)
        else:
            self.userhome = '/home/{0}/.bash_completion'.format(os.getlogin())

        if not BASH_COMPLETION in open(self.userhome, 'r').read():
            with open(self.userhome, 'a') as completion:
                print('Autocomplete was written to {0}'.format(self.userhome))
                completion.write(BASH_COMPLETION)


setup(
    name='geeknote',
    version='0.1',
    license='GPL',
    author='Vitaliy Rodnenko',
    author_email='vitaly@webpp.ru',
    description='Geeknote - is a command line client for Evernote, '
                'that can be use on Linux, FreeBSD and OS X.',
    url='http://www.geeknote.me',
    packages=['geeknote'],
    install_requires=[
        'evernote==1.19',
        'html2text',
        'sqlalchemy',
        'markdown',
        'thrift'
    ],
    entry_points={
        'console_scripts': [
            'geeknote = geeknote.geeknote:main',
            'gnsync = geeknote.gnsync:main'
        ]
    },
    cmdclass={
        'install': full_install
    },
    platforms='Any',
    test_suite='tests',
    keywords='Evernote, console'
)
