import time
import os
from setuptools import setup, find_packages

# local
import config

os.system('rm -rf geeknote')

packages = ['geeknote.' + x for x in find_packages()] + ['geeknote']

# This is to properly encapsulate the library during egg generation
os.system('mkdir geeknote && cp -pr * geeknote/ && rmdir geeknote/geeknote')

setup(
	name = "geeknote",
	version = time.strftime(str(config.VERSION) + '.%Y%m%d.%H%M'),
	packages = packages,
	author = 'Vitaliy Rodnenko',
	author_email = 'vitaly@webpp.ru',
	description = 'terminal-mode geeknote client and synchronizer',
	entry_points = {
		'console_scripts': [
			'geeknote = geeknote.geeknote:main',
			'gnsync = geeknote.gnsync:main',
		]
	}
)
