#!/usr/bin/env python

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
import locale
import time

import io
from oauth import GeekNoteAuth
from storage import Storage
import editor
import tools
from log import logging

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
    storage = None

    def __init__(self):
        self.getStorage()
        self.checkVersion()

        #io.preloader.setMessage('Check OAuth Token..')
        self.checkAuth()

    def getStorage(self):
        if self.storage:
            return self.storage

        self.storage = Storage()
        return self.storage

    def setUserStore(self, store):
        self.userStore = store


    def getUserStore(self):
        if self.userStore:
            return self.userStore

        logging.error("User Store not exist")

    def loadNoteStore(self):
        noteStoreUrl = self.getUserStore().getNoteStoreUrl(self.authToken)
        noteStoreHttpClient = THttpClient.THttpClient(noteStoreUrl)
        noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
        self.noteStore = NoteStore.Client(noteStoreProtocol)

    def getNoteStore(self):
        if self.noteStore:
            return self.noteStore

        self.loadNoteStore()
        return self.noteStore

    def checkVersion(self):
        userStoreHttpClient = THttpClient.THttpClient(self.userStoreUri)
        userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHttpClient)
        self.setUserStore(UserStore.Client(userStoreProtocol))
    
        versionOK = self.getUserStore().checkVersion("Python EDAMTest",
                                       UserStoreConstants.EDAM_VERSION_MAJOR,
                                       UserStoreConstants.EDAM_VERSION_MINOR)
        if not versionOK:
            logging.error("Old EDAM version")
            exit(1)

    def checkAuth(self):
        self.authToken = self.getStorage().getUserToken()
        logging.debug("oAuth token : %s", self.authToken)
        if self.authToken:
            return

        GNA = GeekNoteAuth()
        self.authToken = GNA.getToken()
        userInfo = self.getUserInfo()
        if not isinstance(userInfo, Types.User):
            logging.error("User info not get")

        self.getStorage().createUser(self.authToken, userInfo)

    def getUserInfo(self):
        return self.getUserStore().getUser(self.authToken)
    
    """
    WORK WITH NOTEST
    """
    def findNotes(self, keywords, count):
        nf = NoteStore.NoteFilter()
        if keywords:
            nf.words = keywords
        return self.getNoteStore().findNotes(self.authToken, nf, 0, count)

    def loadNoteContent(self, note):
        """ modify Note object """
        if not isinstance(note, Types.Note):
            raise Exception("Note content must be an instanse of Note, '%s' given." % type(content))

        note.content = self.getNoteStore().getNoteContent(self.authToken, note.guid)

    def createNote(self, title, content, tags=None, notebook=None):
        note = Types.Note()
        note.title = title
        note.content = content

        if tags:
            note.tagNames = tags

        if notebook:
            note.notebookGuid = notebook

        logging.debug("New note : %s", note)

        try: 
            self.getNoteStore().createNote(self.authToken, note)
            return True
        except Exception, e:
            logging.error("Error: %s", str(e))
            return False

    def updateNote(self, guid, title=None, content=None, tags=None, notebook=None):
        note = Types.Note()
        note.guid = guid
        if title:
            note.title = title

        if content:
            note.content = content

        if tags:
            note.tagNames = tags

        if notebook:
            note.notebookGuid = notebook

        logging.debug("Update note : %s", note)

        try: 
            self.getNoteStore().updateNote(self.authToken, note)
            return True
        except Exception, e:
            logging.error("Error: %s", str(e))
            return False

    def deleteNote(self, guid):
        logging.debug("Delete note with guid: %s", guid)
        try: 
            self.getNoteStore().deleteNote(self.authToken, guid)
            return True
        except Exception, e:
            logging.error("Error: %s", str(e))
            return False

    """
    WORK WITH NOTEBOOKS
    """
    def findNotebooks(self):
        return self.getNoteStore().listNotebooks(self.authToken)

    def createNotebook(self, name):
        notebook = Types.Notebook()
        notebook.name = name

        logging.debug("New notebook : %s", notebook)

        try: 
            result = self.getNoteStore().createNotebook(self.authToken, notebook)
            return result
        except Exception, e:
            logging.error("Error: %s", str(e))
            return False

    def updateNotebook(self, guid, name):
        notebook = Types.Notebook()
        notebook.name = name
        notebook.guid = guid

        logging.debug("Update notebook : %s", notebook)

        try: 
            self.getNoteStore().updateNotebook(self.authToken, notebook)
            return True
        except Exception, e:
            logging.error("Error: %s", str(e))
            return False

    def deleteNotebook(self, guid):
        logging.debug("Delete notebook : %s", guid)
        try: 
            self.getNoteStore().expungeNotebook(self.authToken, guid)
            return True
        except Exception, e:
            logging.error("Error: %s", str(e))
            return False


class GeekNoteConnector(object):
    evernote = None
    storage = None
    
    def connectToEvertone(self):
        if self.evernote:
            return

        io.preloader.setMessage("Connect to Evernote...")
        self.evernote = GeekNote()

    def getEvernote(self):
        if self.evernote:
            return self.evernote

        self.connectToEvertone()
        return self.evernote

    def getStorage(self):
        if self.storage:
            return self.storage

        self.storage = self.getEvernote().getStorage()
        return self.storage


class User(GeekNoteConnector):
    """ Work with auth User """

    def info(self, full=True):
        
        info = self.getEvernote().getUserInfo()
        #logging.debug("User info:" % str(info))
        io.showUser(info, True)



class Notebooks(GeekNoteConnector):
    """ Work with auth Notebooks """

    def list(self):
        result = self.getEvernote().findNotebooks()
        io.printList(result)

    def create(self, title):
        self.connectToEvertone()
        io.preloader.setMessage("Creating notepad...")
        result = self.getEvernote().createNotebook(name=title)

        if result:
            io.successMessage("Notepad successfully created")
        else:
            io.failureMessage("Error while creating the note")
            exit(1)

        return result

    def edit(self, notepad, title):

        notebook = self._searchNotebook(notepad)

        io.preloader.setMessage("Updating notepad...")
        result = self.getEvernote().updateNotebook(guid=notebook.guid, name=title)

        if result:
            io.successMessage("Notepad successfully updated")
        else:
            io.failureMessage("Error while creating the note")
            exit(1)

    def remove(self, notepad):

        notebook = self._searchNotebook(notepad)

        if not io.confirm('Are you sure you want to delete this notepad: "%s"' % notebook.name):
            exit(1)

        io.preloader.setMessage("Deleting notepad...")
        result = self.getEvernote().deleteNotebook(guid=notebook.guid)

        if result:
            io.successMessage("Notepad successfully updated")
        else:
            io.failureMessage("Error while creating the note")

    def _searchNotebook(self, notebook):

        result = self.getEvernote().findNotebooks()
        notebook = [item for item in result if item.name == notebook]

        if notebook:
            notebook = notebook[0]

        else:
            notebook = io.SelectSearchResult(result)

        logging.debug("Selected notebook: %s" % str(notebook))
        return notebook

    def getNoteGUID(self, notepad):
        if len(notepad) == 36 and notepad.find("-") == 4:
            return notepad

        result = self.getEvernote().findNotebooks()
        notebook = [item for item in result if item.name == notepad]
        if notebook:
            return notebook[0].guid
        else:
            return None


class Notes(GeekNoteConnector):
    """ Work with Notes """
    
    findExactOnUpdate = False
    selectFirstOnUpdate = False
    def __init__(self, findExactOnUpdate=False, selectFirstOnUpdate=False):
        self.findExactOnUpdate = bool(findExactOnUpdate)
        self.selectFirstOnUpdate = bool(selectFirstOnUpdate)

    def create(self, title, body, tags=None, notepad=None):

        if body == "WRITE_IN_EDITOR":
            logging.debug("launch system editor")
            body = editor.edit()

        else:
            if os.path.isfile(body):
                logging.debug("Load body file")
                body = open(body, "r").read()

            logging.debug("Convert body")
            body = editor.textToENML(body)

        if tags:
            tags = tools.strip(tags.split(','))

        if notepad:
            notepadGuid = Notebooks().getNoteGUID(notepad)
            if notepadGuid is None:
                newNotepad = Notebooks().create(notepad)
                notepadGuid = newNotepad.guid
            
            notepad = notepadGuid
            logging.debug("search notebook")

        self.connectToEvertone()
        io.preloader.setMessage("Creating note...")
        result = self.getEvernote().createNote(title=title, content=body, tags=tags, notebook=notepad)

        if result:
            io.successMessage("Note successfully created")
        else:
            io.failureMessage("Error while creating the note")

    def edit(self, note, title=None, body=None, tags=None, notepad=None):

        self.connectToEvertone()
        note = self._searchNote(note)

        if not title:
            title = note.title

        if body:
            if body == "WRITE_IN_EDITOR":
                logging.debug("launch system editor")
                self.getEvernote().loadNoteContent(note)
                body = editor.edit(note.content)

            else:
                if os.path.isfile(body):
                    logging.debug("Load body file")
                    body = open(body, "r").read()

                logging.debug("Convert body")
                body = editor.textToENML(body)

        if tags:
            tags = tools.strip(tags.split(','))

        if notepad:
            notepadGuid = Notebooks().getNoteGUID(notepad)
            if notepadGuid is None:
                newNotepad = Notebooks().create(notepad)
                notepadGuid = newNotepad.guid
            
            notepad = notepadGuid
            logging.debug("search notebook")

        
        io.preloader.setMessage("Saving note...")
        result = self.getEvernote().updateNote(guid=note.guid, title=title, content=body, tags=tags, notebook=notepad)

        if result:
            io.successMessage("Note successfully saved")
        else:
            io.failureMessage("Error while saving the note")

    def remove(self, note):

        self.connectToEvertone()
        note = self._searchNote(note)

        if not io.confirm('Are you sure you want to delete this note: "%s"' % note.title):
            exit(1)

        io.preloader.setMessage("Deleting note...")
        result = self.getEvernote().deleteNote(note.guid)

        if result:
            io.successMessage("Note successful deleted")
        else:
            io.failureMessage("Error while deleting the note")

    def show(self, note):

        self.connectToEvertone()

        note = self._searchNote(note)

        io.preloader.setMessage("Loading note...")
        self.getEvernote().loadNoteContent(note)

        io.showNote(note)


    def _searchNote(self, note):
        note = tools.strip(note)
        if tools.checkIsInt(note):
            # TODO request in storage
            # TMP >>>
            result = self.getEvernote().findNotes(None, 1)
            note = result.notes[0]
            # TMP <<<

        else:
            if self.findExactOnUpdate:
                request = 'intitle:"%s"' % note if note else None
            else:
                request = "intitle:%s" % note if note else None

            logging.debug("Search notes: %s" % request)
            result = self.getEvernote().findNotes(request, 20)

            logging.debug("Search notes result: %s" % str(result))
            if result.totalNotes == 0:
                io.successMessage("Notes not found")
                exit(1)

            elif result.totalNotes == 1 or self.selectFirstOnUpdate:
                note = result.notes[0]

            else:
                logging.debug("Choose notes: %s" % str(result.notes)) 
                note = io.SelectSearchResult(result.notes)

        logging.debug("Selected note: %s" % str(note))
        return note


    def find(self, search=None, tags=None, notepads=None, date=None, count=None, exact_entry=None, content_search=None, url_only=None, ):

        request = ""
        if search:
            search = tools.strip(search)
            if exact_entry:
                search = '"%s"' % search

            if content_search:
                request += "any:%s " % search 
            else:
                request += "intitle:%s " % search

        if tags:
            for tag in tools.strip(tags.split(',')):

                if tag.startswith('-'):
                    request +="-tag:%s " % tag[1:]
                else:
                    request +="tag:%s " % tag

        if date:
            date = tools.strip(date.split('-'))
            try:
                start_date =  time.strptime(date[0], "%d.%m.%Y")
                request +="created:%s " % time.strftime("%Y%m%d", start_date)
                
                if len(date) == 2:
                    request += "-created:%s " % time.strftime("%Y%m%d", time.strptime(date[1], "%d.%m.%Y"))
                else:
                    request += "-created:%s " % time.strftime("%Y%m%d", time.gmtime(time.mktime(start_date)+60*60*24*2))
                
            except ValueError, e:
                io.failureMessage('Incorrect date format in --date attribute. Format: %s' % time.strftime("%d.%m.%Y", time.strptime('19991231', "%Y%m%d")))
                exit(1)

        if notepads:
            for notepad in tools.strip(notepads.split(',')):
                if notepad.startswith('-'):
                    request += "-notebook:%s " % tools.strip(notepad[1:])
                else:
                    request += "notebook:%s " % tools.strip(notepad)

        if not count:
            count = 20

        logging.debug("Search request: %s", request)
        logging.debug("Search count: %s", count)
        
        result = self.getEvernote().findNotes(request, count)

        if result.totalNotes == 0:
            io.successMessage("Notes not found")

        # TODO Save result to storage

        io.SearchResult(result.notes, request)

if __name__ == "__main__":

    COMAND = sys.argv[1] if len(sys.argv) >= 2 else ""

    # run check & run autocomplete
    if COMAND == "autocomplete":
        sys.argv = sys.argv[2:] # remove autocomplete from args list
        import argparser
        
        argparser.printAutocomplete()
        exit(1)

    import argparser

    ARGS = argparser.parse()

    logging.debug("CLI options: %s", str(ARGS))

    # Users
    if COMAND == 'user':
        User().info(**ARGS)

    # Notes
    if COMAND == 'create':
        Notes().create(**ARGS)

    if COMAND == 'edit':
        Notes().edit(**ARGS)

    if COMAND == 'remove':
        Notes().remove(**ARGS)

    if COMAND == 'show':
        Notes().show(**ARGS)

    if COMAND == 'find':
        Notes().find(**ARGS)

    # Notebooks
    if COMAND == 'list-notepad':
        Notebooks().list(**ARGS)

    if COMAND == 'create-notepad':
        Notebooks().create(**ARGS)

    if COMAND == 'edit-notepad':
        Notebooks().edit(**ARGS)

    if COMAND == 'remove-notepad':
        Notebooks().remove(**ARGS)
