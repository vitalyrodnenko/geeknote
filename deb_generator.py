#!/usr/bin/env python
#-*- coding:utf-8 -*-

from glob import glob
import os

from py2deb import Py2deb

p=Py2deb("geeknote")

p.author="Vitaliy Rodnenko, Simon Moiseenko, Ivan Gureev"
p.mail="vitaly@webpp.ru"
p.description="Geeknote - is a command line client for Evernote, that can be use on Linux, FreeBSD and OS X."
p.url = "http://geeknote.me"
p.depends="python"
p.license="gpl"
p.section="utils"
p.arch="all"

# application
p["/usr/bin"] = ["deb/geeknote.py|geeknote", "deb/gnsync.py|gnsync"]

# bash auto complite
p["/etc/bash_completion.d"] = ["bash_completion/geeknote|geeknote"]

# lib files
dir_name='lib'
install_dir = '/usr/local/lib/geeknone'

items = {}
items[install_dir] = []
for root, dirs, files in os.walk(dir_name):
	fake_file = []
	for f in files:
		file_name, file_extension = os.path.splitext(root + os.sep + f)
		if file_extension != '.pyc':
	 		fake_file.append(root + os.sep + f)

	if len(fake_file) > 0:
  		items[install_dir].extend(fake_file)

# project files
project_files = ["geeknote.py", "gnsync.py" ,"argparser.py", "editor.py", "log.py", "oauth.py", "out.py", "storage.py", "tools.py", "config.py"]
items[install_dir].extend(project_files)

for key, value in items.items():
	p[key] = value

# start deb generating
p.generate("0.0.1")