# -*- coding: utf-8 -*-
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append( os.path.join(PROJECT_ROOT, 'lib') )

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

from unit import editorTest
suite.addTest(editorTest.suite())


unittest.TextTestRunner(verbosity=2).run(suite)