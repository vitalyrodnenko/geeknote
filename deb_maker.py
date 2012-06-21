#!/usr/bin/env python
#-*- coding:utf-8 -*-

from glob import glob
import os

from py2deb import Py2deb

p=Py2deb("geeknote")

p.author="Ivan Gureev, Vitaliy Rodnenko, Simon Moiseenko"
p.mail="vitaly@webpp.ru"
p.description="Geeknote - is a command line client for Evernote, that can be use on Linux, FreeBSD and OS X."
p.url = "http://geeknote.me"
p.depends="python"
p.license="gpl"
p.section="utils"
p.arch="all"

p["/usr/bin"] = ["geeknote.py|geeknote", "gnsync.py|gnsync"]

p["/etc/bash_completion.d"] = ["bash_completion/geeknote"]

# p["/usr/local/lib/geeknone"] = ["lib"]
# p["/usr/local/lib/geeknone"] = glob("unit/*.*")

p["/usr/local/lib/geeknone"] = ["geeknote.py" ,"argparser.py", "editor.py", "log.py", "oauth.py", "out.py", "storage.py", "tools.py"]

p.generate("0.0.1")