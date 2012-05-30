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
from xml.dom.minidom import DOMImplementation
import html2text
import markdown

CONSUMER_KEY = 'skaizer-1250'
CONSUMER_SECRET = 'ed0fcc0c97c032a5'

class GeekNote:

    consumerKey = CONSUMER_KEY
    consumerSecret = CONSUMER_SECRET
    userStoreUri = "https://sandbox.evernote.com/edam/user"
    authToken = "S=s1:U=2374b:E=13ef15cf7d7:C=13799abcbd7:P=185:A=stepler-8439:H=c9f34ca532df2df1b6593f2f504f1c5c"
    userStore = None
    noteStore = None

    def __init__(self):
        self.getStorage()
        self.getSettings()

        io.preloader.setMessage('Check SDK version...')
        self.checkVersion()

        io.preloader.setMessage('Check OAuth Token..')
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
        print self.authToken
        # TODO save token to storage
    
    def getNoteStore(self):
        io.preloader.setMessage('Connect to Notes...')

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

        io.preloader.setMessage('Search Notes...')
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

    def editNote(self, name, full):
        io.preloader.stop()
        note = self.getNote(name, full)
        EDITOR = os.environ.get('EDITOR','nano')
        """
        with tempfile.NamedTemporaryFile(suffix=".txt") as tmpfile:
            tmpfile.write(str(note.content))
            tmpfile.flush()
            call([EDITOR, tmpfile.name])
            for line in tmpfile.readlines():
                print line
            tmpfile.close()
        """

        tmpfile = tempfile.NamedTemporaryFile(mode='w+t', delete=False, suffix=".html")
        tmpfile.write(html2text.html2text(str(note.content)))
        tmpfile.flush()
        n = tmpfile.name
        tmpfile.close()
        call([EDITOR, n])
        newfile = open(n)
        newnote = newfile.read()
        newfile.close()
        os.remove(n)
        #self.createNote("New", newnote)

        return 1

    def _convertToHTML(self, note):
        noteHTML = markdown.markdown(note)
        return noteHTML

    def _parseNoteToMarkDown(self, note):    
        txt = html2text.html2text(note.decode('utf-8','ignore'))
        return txt#.decode('utf-8', 'replace')

    def _wrapNotetoHTML(self, noteBody):
        mytext = '''<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml.dtd">
<en-note>'''
        mytext += self._convertToHTML(noteBody)
        mytext += "</en-note>"
        return mytext

    def editNote(self, noteid):
        note = self.getNote(noteid, noteid)

        io.preloader.stop()

        """
        note = Types.Note()
        note = self.getNote(self.noteName, False)
        """
        oldNote = self._parseNoteToMarkDown(note.content)
     
        (fd, tfn) = tempfile.mkstemp()
        
        os.write(fd, oldNote)
        os.close(fd)
        editor = os.environ.get("editor")
        if not (editor):
            editor = os.environ.get("EDITOR")
        if not (editor):
            editor = "nano"
        os.system(editor + " " + tfn)
        file = open(tfn, 'r')
        contents = file.read()

        print contents

        #noteContent = self._wrapNotetoHTML(contents)
        #note.content = noteContent
        #self.noteStore.updateNote(self.authToken, note)


        return
        try:
            noteContent = self._wrapNotetoHTML(contents)
            note.content = noteContent
            self.noteStore.updateNote(self.authToken, note)
        except:
            print "Your XML was malformed. Edit again (Y/N)?"
            answer = ""
            while (answer.lower() != 'n' and answer.lower() != 'y'):
                answer = getInput()
            if (answer.lower() == 'y'):
                self.editNote()



def getInput():
    mystring = ""
    while(True):
        line = sys.stdin.readline()
        if not line:
            break
        mystring += line
    return mystring


gn = GeekNote()

gn.getNoteStore()
#print gn.getAllNotes(10)
print gn.editNote("Test")