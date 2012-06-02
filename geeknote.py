# -*- coding: utf-8 -*-
# add Evernote SDK
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EVERNOTE_SDK = os.path.join(PROJECT_ROOT, 'lib')
sys.path.append( EVERNOTE_SDK )

import sys
import hashlib
import binascii
import time
import thrift.protocol.TBinaryProtocol as TBinaryProtocol
import thrift.transport.THttpClient as THttpClient
import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.type.ttypes as Types
import evernote.edam.error.ttypes as Errors

import io
from oauth import GeekNoteAuth

import tempfile
import os
from subprocess import call
import html2text
import markdown
import md5
from tools import confirm

CONSUMER_KEY = 'skaizer-1250'
CONSUMER_SECRET = 'ed0fcc0c97c032a5'

class GeekNote:

    consumerKey = CONSUMER_KEY
    consumerSecret = CONSUMER_SECRET
    userStoreUri = "https://sandbox.evernote.com/edam/user"
    authToken = None
    #authToken = "S=s1:U=2265a:E=13ee295740c:C=1378ae4480c:P=185:A=stepler-8439:H=8bfb5c7a5bd5517eb885034cf5d515b2"
    authToken = "S=s1:U=2374b:E=13ef15cf7d7:C=13799abcbd7:P=185:A=stepler-8439:H=c9f34ca532df2df1b6593f2f504f1c5c"
    userStore = None
    noteStore = None

    def __init__(self):
        self.getStorage()
        self.getSettings()

        
        self.checkVersion()

        #io.preloader.setMessage('Check OAuth Token..')
        self.checkAuth()

    def getStorage(self):
        # TODO access to sqlite
        pass

    def getSettings(self):
        # TODO load settings from storage
        pass

    def saveToken(self):
        # TODO save account to storage
        pass

    def checkVersion(self):
        userStoreHttpClient = THttpClient.THttpClient(self.userStoreUri)
        userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHttpClient)
        self.userStore = UserStore.Client(userStoreProtocol)
    
        versionOK = self.userStore.checkVersion("Python EDAMTest",
                                       UserStoreConstants.EDAM_VERSION_MAJOR,
                                       UserStoreConstants.EDAM_VERSION_MINOR)
        if not versionOK:
            print "Old EDAM version"
            exit(1)

    def checkAuth(self):
        # load from storage 
        
        if self.authToken:
            return

        GNA = GeekNoteAuth()
        self.authToken = GNA.getToken()
        # print self.authToken
        # TODO save token to storage
    
    def getNoteStore(self):
        #io.preloader.setMessage('Connect to Notes...')

        noteStoreUrl = self.userStore.getNoteStoreUrl(self.authToken)
        noteStoreHttpClient = THttpClient.THttpClient(noteStoreUrl)
        noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
        self.noteStore = NoteStore.Client(noteStoreProtocol)

    def findNotes(self, count, keywords):
        nf = NoteStore.NoteFilter()
        nf.words = keywords
        return self.noteStore.findNotes(self.authToken, nf, 0, count)

    def getAllNotes(self, maxNotes=20):
        if not self.noteStore:
            self.getNoteStore()

        #io.preloader.setMessage('Search Notes...')
        return self.noteStore.findNotes(self.authToken, NoteStore.NoteFilter(), 0, maxNotes)

    def getNote(self, name, full):
        notelist = self.findNotes(10,name)
        #for note in notelist.notes:
        if (len(notelist.notes) == 0):
            return None
        notelist.notes[0].content = self.noteStore.getNoteContent(self.authToken, notelist.notes[0].guid)
        return notelist.notes[0]

    def createNote(self, title, text):
        if not self.noteStore:
            self.getNoteStore()

        newNote = Types.Note()
        newNote.title = title
        newNote.content = text
        self.noteStore.text(self.authToken, newNote)

        return self.noteStore.createNote(self.authToken, note)

    def _convertToHTML(self, note):
        note = unicode(note,"utf-8")
        noteHTML = markdown.markdown(note)
        return noteHTML.encode("utf-8")

    def _parseNoteToMarkDown(self, note):
        note = note.decode('utf-8')
        txt = html2text.html2text(note)
        return txt.encode('utf-8')

    def _wrapNotetoHTML(self, noteBody):
        """
        Create an ENML format of note.
        """
        mytext = '''<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml.dtd">
<en-note>'''
        mytext += self._convertToHTML(noteBody)
        mytext += "</en-note>"
        return mytext

    def editNote(self, noteid):
        """
        Call the system editor, that types as a default in the system.
        Editing goes in markdown format, and then the markdown converts into HTML, before uploading to Evernote.
        """

        # ВНИМАНИЕ: Следующую строку надо переделать. Сейчас требуется передавать 2 аргумента функции, второй ничего не делает. Когда переделается метод, надо исправить этот кусок.
        note = self.getNote(noteid, noteid)

        io.preloader.stop()

        oldNote = self._parseNoteToMarkDown(note.content)
     
        (fd, tfn) = tempfile.mkstemp()
        
        os.write(fd, oldNote)
        os.close(fd)
        
        # Try to find default editor in the system.
        editor = os.environ.get("editor")
        if not (editor):
            editor = os.environ.get("EDITOR")
        if not (editor):
            # If default editor is not finded, then use nano as a default.
            editor = "nano"
        
        # Make a system call to open file for editing.
        os.system(editor + " " + tfn)
        file = open(tfn, 'r')
        newNote = file.read()

        # Check the note is changed. If it's not, then nothing to save.
        if md5.md5(oldNote).hexdigest() != md5.md5(newNote).hexdigest():

            # Convert markdown to HTML.
            noteContent = self._wrapNotetoHTML(newNote)
            try:
                # Try to submit changes.
                note.content = noteContent
                # Upload changes
                self.noteStore.updateNote(self.authToken, note)
            except:
                # If it's an error we can edit our note again.
                if confirm("Your XML is not correct. Edit again?"):
                    self.editNote(noteid)
        else:
            print "Note wasn't edited. Nothing to save."

gn = GeekNote()
gn.getNoteStore()
gn.editNote("Test")

class Notes(object):

    evernote = None
    def __init__(self):
        io.preloader.setMessage('Connect to Evernote...')

        self.evernote = GeekNote()

    """ Работа с заметками"""
    def find(self):
        io.preloader.setMessage('Search...')

        result = self.evernote.getAllNotes()
        if result.totalNotes == 0:
            print "notes not found"

        notes = dict( (index+1, {'title': item.title, 'guid': item.guid}) for index, item in enumerate(result.notes) )
        # TODO Save result to storage

        # print results
        io.SearchResult(notes)