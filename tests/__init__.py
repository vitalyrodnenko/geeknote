# -*- coding: utf-8 -*-
import os
import sys
import unittest

#PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#sys.path.append(os.path.join(PROJECT_ROOT, 'lib'))

from geeknote import tools

# disable interrupt
tools.exit = lambda: 'exit'

suite = unittest.TestSuite()
suite.addTests(unittest.TestLoader().loadTestsFromModule('tests'))

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)
