# -*- coding: utf-8 -*-

from editor import *
import unittest

class testEditor(unittest.TestCase):

    def setUp(self):
        self.MD_TEXT = \
"""# Header 1
## Header 2
Line 1
*Line 2*
**Line 3**"""
        self.HTML_TEXT = \
"""<h1>Header 1</h1><h2>Header 2</h2><p>Line 1<br /><em>Line 2</em><br /><strong>Line 3</strong></p>"""
    def testTextToENML(self):
        self.assertEqual(textToENML(self.MD_TEXT), wrapENML(self.HTML_TEXT))

    # def testENMLToText(self):
    #     self.assertEqual(ENMLtoText( wrapENML(self.HTML_TEXT)), self.MD_TEXT)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testEditor))
    return suite