# -*- coding: utf-8 -*-
import unittest
from geeknote import config
from geeknote.geeknote import User, Notebooks, Notes, GeekNote
from geeknote.storage import Storage
from random import SystemRandom
from string import hexdigits

# see https://docs.python.org/2.7/library/unittest.html §25.3.6
# http://thecodeship.com/patterns/guide-to-python-function-decorators/
# (decorator with empty argument list)
def skipUnlessDevMode():
    if config.DEV_MODE:
        return lambda x: x
    else:
        return unittest.skip("Test only active with DEV_MODE=True")

class TestSandbox(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # start out with empty auth token. Save current token to restore it later.
        cls.storage = Storage()
        cls.token = cls.storage.getUserToken()
        cls.info = cls.storage.getUserInfo()
        cls.storage.removeUser()
        cls.notes = set()
        cls.nbs = set()
        cls.notebook = ("Geeknote test %s please delete" %
                        "".join(SystemRandom().choice(hexdigits) for x in range(12)))

    @classmethod
    def tearDownClass(cls):
        if cls.token:
            cls.storage.createUser(cls.token, cls.info)

    def setUp(self):
        self.user = User()
        self.tag = "geeknote_unittest_1"
        self.Notes = Notes()
        self.Notebooks = Notebooks()
        self.Geeknote = self.Notebooks.getEvernote()
        
    @skipUnlessDevMode()
    def test01_userLogin(self):
        # This is an implicit test. The GeekNote() call in setUp() will perform
        # an automatic login.
        self.assertTrue(self.Geeknote.checkAuth())

    @skipUnlessDevMode()
    def test10_createNotebook(self):
        self.assertTrue(self.Notebooks.create(self.notebook))

    @skipUnlessDevMode()
    def test15_findNotebook(self):
        all = self.Geeknote.findNotebooks()
        nb = [nb for nb in all if nb.name == self.notebook]
        self.assertTrue(len(nb)==1)
        self.nbs.add(nb[0].guid)

    @skipUnlessDevMode()
    def test30_createNote(self):
        self.Notes.create("note title 01",
                          content = """\
# Sample note 01
This is the note text.
""",
                          notebook = self.notebook,
                          tags = self.tag)

    @skipUnlessDevMode()
    def test31_findNote(self):
        self.Notes.find(notebooks=self.notebook, tags=self.tag)
        result = self.storage.getSearch()
        self.assertTrue(len(result.notes)==1)
        self.notes.add(result.notes[0].guid)

    @skipUnlessDevMode()
    def test90_removeNotes(self):
        while self.notes:
            self.assertTrue(self.Geeknote.removeNote(self.notes.pop()))

    # EXPECTED FAILURE
    # "This function is generally not available to third party applications"
    # https://dev.evernote.com/doc/reference/NoteStore.html#Fn_NoteStore_expungeNotebook
    @skipUnlessDevMode()
    def test95_removeNotebooks(self):
        while self.nbs:
            #self.assertTrue(self.Geeknote.removeNotebook(self.nbs.pop()))
            self.assertRaises(SystemExit, self.Geeknote.removeNotebook, self.nbs.pop())

    @skipUnlessDevMode()
    def test99_userLogout(self):
        self.user.logout(force=True)
        self.assertFalse(self.Geeknote.checkAuth())

