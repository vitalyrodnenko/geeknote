# -*- coding: utf-8 -*-

import os, sys

# path to libs in unix systems
sys.path.append( os.path.join('/', 'usr', 'local', 'lib', 'geeknone'))

import unittest
import out
import tools

# отключаем вывод на печать
out.printLine = lambda x, y=None: ''

# отключаем прерывание
tools.exit = lambda : 'exit'

suite = unittest.TestSuite()

from unit import argparserTest
suite.addTest(argparserTest.suite())

from unit import geeknoteTest
suite.addTest(geeknoteTest.suite())


unittest.TextTestRunner(verbosity=2).run(suite)