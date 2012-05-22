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

CONSUMER_KEY = 'stepler-8439'
CONSUMER_SECRET = '4b4e6661ed1f2a5c'

class GeekNote:

    user = 'simon@webpp.ru'
    password = '5t3pl3r'

    consumerKey = CONSUMER_KEY
    consumerSecret = CONSUMER_SECRET
    userStoreUri = "https://sandbox.evernote.com/edam/user"
    noteStoreUriBase = "http://sandbox.evernote.com/edam/note/"
    authToken = None
    authResult = None
    noteStore = None


    def getStorage(self):
        # TODO access to sqlite
        pass

    def getSettings(self):
        # TODO load settings from storage
        pass

    def saveUserAccount(self):
        # TODO save account to storage
        pass

    def getAuth(self):

        if not (self.user and self.password):
            self.user, self.password = io.GetUserCredentials()
            self.saveUserAccount()


        userStoreHttpClient = THttpClient.THttpClient(self.userStoreUri)
        userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHttpClient)
        userStore = UserStore.Client(userStoreProtocol)
    
        versionOK = userStore.checkVersion("Python EDAMTest",
                                       UserStoreConstants.EDAM_VERSION_MAJOR,
                                       UserStoreConstants.EDAM_VERSION_MINOR)
        if not versionOK:
            print "Old EDAM version"
            exit(1)
        print self.user, self.password, self.consumerKey, self.consumerSecret
        authResult = userStore.authenticate(self.user, self.password, self.consumerKey, self.consumerSecret)
        user = authResult.user
        self.authToken = authResult.authenticationToken
        self.authResult = authResult
        return self.authToken
    
    def getNoteStore(self):
        noteStoreUri = self.noteStoreUriBase + self.authResult.user.shardId
        noteStoreHttpClient = THttpClient.THttpClient(noteStoreUri)
        noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
        self.noteStore = NoteStore.Client(noteStoreProtocol)

    def getAllNotes(self, maxNotes):
        return self.noteStore.findNotes(self.authToken, NoteStore.NoteFilter(), 0, maxNotes)

gn = GeekNote()
gn.getAuth()
gn.getNoteStore()
print gn.getAllNotes()