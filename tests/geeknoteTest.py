# -*- coding: utf-8 -*-

import unittest
from geeknote.geeknote import *
from geeknote import tools
from geeknote import editor

editor.edit = lambda x=None: "%s from text editor" % x


class GeekNoteOver(GeekNote):
    def __init__(self):
        pass

    def loadNoteContent(self, note):
        note.content = "note content"


class NotesOver(Notes):
    def connectToEvertone(self):
        self.evernote = GeekNoteOver()


class testNotes(unittest.TestCase):

    def setUp(self):
        self.notes = NotesOver()
        self.testNote = tools.Struct(title="note title")

    def test_parceInput1(self):
        testData = self.notes._parceInput("title", "test body", "tag1")
        self.assertTrue(isinstance(testData, dict))
        if not isinstance(testData, dict):
            return

        self.assertEqual(testData['title'], "title")
        self.assertEqual(testData['content'], editor.textToENML("test body"))
        self.assertEqual(testData["tags"], ["tag1", ])

    def test_parceInput2(self):
        testData = self.notes._parceInput("title", "WRITE", "tag1, tag2",
                                          None, self.testNote)
        self.assertTrue(isinstance(testData, dict))
        if not isinstance(testData, dict):
            return

        self.assertEqual(testData['title'], "title")
        self.assertEqual(
            testData['content'],
            editor.textToENML("note content from text editor")
        )
        self.assertEqual(testData["tags"], ["tag1", "tag2"])

    def test_createSearchRequest1(self):
        testRequest = self.notes._createSearchRequest(
            search="test text",
            tags="tag1",
            notebooks="test notebook",
            date="01.01.2000",
            exact_entry=True,
            content_search=True
        )
        response = 'notebook:"test notebook" tag:"tag1" ' \
                   'created:20000101 -created:20000102 "test text"'
        self.assertEqual(testRequest, response)

    def test_createSearchRequest2(self):
        testRequest = self.notes._createSearchRequest(
            search="test text",
            tags="tag1, tag2",
            notebooks="notebook1, notebook2",
            date="31.12.1999-31.12.2000",
            exact_entry=False,
            content_search=False
        )
        response = 'notebook:"notebook1" notebook:"notebook2" tag:"tag1"' \
                   ' tag:"tag2" created:19991231 -created:20010101 ' \
                   'intitle:test text'
        self.assertEqual(testRequest, response)

    def testError_createSearchRequest1(self):
        testRequest = self.notes._createSearchRequest(search="test text",
                                                      date="12.31.1999")
        self.assertEqual(testRequest, 'exit')
