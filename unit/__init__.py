# -*- coding: utf-8 -*-
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append( os.path.join(PROJECT_ROOT, 'lib') )

import unittest
from geeknote import out
from geeknote import tools

import argparserTest
import geeknoteTest
import editorTest

# disable printing
out.printLine = lambda x, y=None: ''

# disable interrupt
tools.exit = lambda : 'exit'

suite = unittest.TestSuite()
suite.addTest(argparserTest.suite())
suite.addTest(geeknoteTest.suite())
suite.addTest(editorTest.suite())

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)