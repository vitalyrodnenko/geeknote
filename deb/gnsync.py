#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os, sys

# path to libs in unix systems
sys.path.insert(0, os.path.join('/', 'usr', 'local', 'lib', 'geeknone'))
sys.path.insert(0, os.path.join('/', 'usr', 'local', 'lib', 'geeknone', 'lib'))

import gnsync

# start application
gnsync.main()