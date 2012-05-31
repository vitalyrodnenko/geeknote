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
import argparse

import io
from oauth import GeekNoteAuth

CONSUMER_KEY = 'skaizer-1250'
CONSUMER_SECRET = 'ed0fcc0c97c032a5'

class GeekNote:

    consumerKey = CONSUMER_KEY
    consumerSecret = CONSUMER_SECRET
    userStoreUri = "https://sandbox.evernote.com/edam/user"
    authToken = None
    #authToken = "S=s1:U=2265a:E=13ee295740c:C=1378ae4480c:P=185:A=stepler-8439:H=8bfb5c7a5bd5517eb885034cf5d515b2"
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

class Notes(object):
    """Работа с заметками"""
    evernote = None
    def __init__(self):
        io.preloader.setMessage('Connect to Evernote...')

        self.evernote = GeekNote()

    
    def find(self):
        io.preloader.setMessage('Search...')

        result = self.evernote.getAllNotes()
        if result.totalNotes == 0:
            print "notes not found"

        notes = dict( (index+1, {'title': item.title, 'guid': item.guid}) for index, item in enumerate(result.notes) )
        # TODO Save result to storage

        # print results
        io.SearchResult(notes)

COMMANDS = {
    "create": {
        "help": "Create note", 
        "arguments": {
            "--title": {"help": "Set note title", "required": True}, 
            "--body": {"help": "Set note content", "required": True} 
            "--tag", 
            "--location"
        }
    },
    "edit": ["--id", "--title", "--body", "--tag", "--location"],
    "remove": ["--id"],
    "find": ["--tag", "--notepad", "--force", "--exact-entry", "--count", "--url-only"],
    "fix": [],
}

if __name__ == "__main__":
    

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='List of commands')

    # A create command
    create_parser = subparsers.add_parser('create', help='Create note')
    create_parser.add_argument('--title', help='Set note title', required=True)
    create_parser.add_argument('--body', help='Set note content', required=True)
    create_parser.add_argument('--tag', help='Add tag to note')
    create_parser.add_argument('--location', help='Add location marker to note')

    # A edit command
    edit_parser = subparsers.add_parser('edit', help='Edit a note')
    edit_parser.add_argument('--id', help='Note ID or position note in last search', required=True)
    edit_parser.add_argument('--title', help='Set note title')
    edit_parser.add_argument('--body', help='Set note content')
    edit_parser.add_argument('--tag', help='Add tag to note')
    edit_parser.add_argument('--location', help='Add location marker to note')

    # A remove command
    edit_parser = subparsers.add_parser('remove', help='Edit a note')
    edit_parser.add_argument('--id', help='Note ID or position note in last search', required=True)

    # A create command
    create_parser = subparsers.add_parser('find', help='Find notes')
    create_parser.add_argument('--exact-entry', help='exact-entry')
    create_parser.add_argument('--tag', help='Search by tags')
    create_parser.add_argument('--notepad', help='Search by notepad')
    create_parser.add_argument('--url-only', help='Display url instead of snippet')

    print parser.parse_args()