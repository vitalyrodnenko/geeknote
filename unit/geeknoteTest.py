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

    def test_parceInput1(self):
        testData = self.notes._parceInput("title", "test body", "tag1")
        self.assertIsInstance(testData, dict)
        if not isinstance(testData, dict): return

        self.assertEqual(testData['title'], "title")
        self.assertEqual(testData['content'], editor.textToENML("test body"))
        self.assertEqual(testData["tags"], ["tag1", ])

    def test_parceInput2(self):
        testData = self.notes._parceInput("title", "WRITE_IN_EDITOR", "tag1, tag2", None, self.testNote)
        self.assertIsInstance(testData, dict)
        if not isinstance(testData, dict): return

        self.assertEqual(testData['title'], "title")
        self.assertEqual(testData['content'], editor.textToENML("note content from text editor"))
        self.assertEqual(testData["tags"], ["tag1", "tag2"])

    def test_createSearchRequest1(self):
        testRequest = self.notes._createSearchRequest(search="test text", tags="tag1", 
            notebooks="test notebook", date="31.12.1999", exact_entry=True, content_search=True)
        self.assertEqual(testRequest, 'any:"test text" tag:"tag1" created:"19991231" -created:"20000101" notebook:"test notebook" ')

    def test_createSearchRequest2(self):
        testRequest = self.notes._createSearchRequest(search="test text", tags="tag1, tag2", 
            notebooks="notebook1, notebook2", date="31.12.1999-31.12.2000", exact_entry=False, content_search=False)
        self.assertEqual(testRequest, 'intitle:test text tag:"tag1" tag:"tag2" created:"19991231" -created:"20001231" notebook:"notebook1" notebook:"notebook2" ')

    def testError_createSearchRequest1(self):
        testRequest = self.notes._createSearchRequest(search="test text", date="12.31.1999")
        self.assertEqual(testRequest, 'exit')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testNotes))
    return suite