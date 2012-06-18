# -*- coding: utf-8 -*-
import unittest
import out

#отключаем вывод на печать
out.printLine = lambda x: pass

suite = unittest.TestSuite()

from unit import argparserTest
suite.addTest(argparserTest.suite())


unittest.TextTestRunner(verbosity=2).run(suite)
