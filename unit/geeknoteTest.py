# -*- coding: utf-8 -*-

from geeknote import *
import unittest
import tools
import editor

editor.edit = lambda x=None: x+" from text editor"

class GeekNoteOver(GeekNote):
    def __init__(self):
        pass

    def loadNoteContent(self, note):
        note.content="note content"

class NotesOver(Notes):
    def connectToEvertone(self):
        self.evernote = GeekNoteOver()


class testNotes(unittest.TestCase):

    def setUp(self):
        self.notes = NotesOver()
        self.testNote = tools.Struct(title="note title")

    def test_parseInput1(self):
        testData = self.notes._parseInput("title", "test body","tag1", None, ["res 1", "res 2"])
        self.assertIsInstance(testData, dict)
        if not isinstance(testData, dict): return

        self.assertEqual(testData['title'], "title")
        self.assertEqual(testData['content'], editor.textToENML("test body"))
        self.assertEqual(testData["tags"], ["tag1", ])
        self.assertEqual(testData["resources"], ["res 1", "res 2"])

    def test_parseInput2(self):
        testData = self.notes._parseInput("title", "WRITE", "tag1, tag2", None, None, self.testNote)
        self.assertIsInstance(testData, dict)
        if not isinstance(testData, dict): return

        self.assertEqual(testData['title'], "title")
        self.assertEqual(testData['content'], editor.textToENML("note content from text editor"))
        self.assertEqual(testData["tags"], ["tag1", "tag2"])

    def test_createSearchRequest1(self):
        testRequest = self.notes._createSearchRequest(search="test text", tags="tag1", 
            notebooks="test notebook", date="01.01.2000", exact_entry=True, content_search=True)
        self.assertEqual(testRequest, 'notebook:"test notebook" tag:"tag1" created:19991231 -created:20000101 "test text"')

    def test_createSearchRequest2(self):
        testRequest = self.notes._createSearchRequest(search="test text", tags="tag1, tag2", 
            notebooks="notebook1, notebook2", date="31.12.1999-31.12.2000", exact_entry=False, content_search=False)
        self.assertEqual(testRequest, 'notebook:"notebook1" notebook:"notebook2" tag:"tag1" tag:"tag2" created:19991231 -created:20001231 intitle:test text')

    def testError_createSearchRequest1(self):
        testRequest = self.notes._createSearchRequest(search="test text", date="12.31.1999")
        self.assertEqual(testRequest, 'exit')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testNotes))
    return suite
