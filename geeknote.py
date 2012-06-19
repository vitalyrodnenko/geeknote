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

import out
from argparser import argparser
from oauth import GeekNoteAuth
from storage import Storage
import editor
import tools
from log import logging

CONSUMER_KEY = 'skaizer-1250'
CONSUMER_SECRET = 'ed0fcc0c97c032a5'

class GeekNote(object):

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
        self.getUserStore()
        self.checkVersion()
        self.checkAuth()

    def getStorage(self):
        if GeekNote.storage:
            return GeekNote.storage

        GeekNote.storage = Storage()
        return GeekNote.storage

    def getUserStore(self):
        if GeekNote.userStore:
            return GeekNote.userStore

        userStoreHttpClient = THttpClient.THttpClient(self.userStoreUri)
        userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHttpClient)
        GeekNote.userStore = UserStore.Client(userStoreProtocol)
    
        return GeekNote.userStore

    def getNoteStore(self):
        if GeekNote.noteStore:
            return GeekNote.noteStore

        noteStoreUrl = self.getUserStore().getNoteStoreUrl(self.authToken)
        noteStoreHttpClient = THttpClient.THttpClient(noteStoreUrl)
        noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
        GeekNote.noteStore = NoteStore.Client(noteStoreProtocol)

        return GeekNote.noteStore

    def checkVersion(self):
        versionOK = self.getUserStore().checkVersion("Python EDAMTest",
                                       UserStoreConstants.EDAM_VERSION_MAJOR,
                                       UserStoreConstants.EDAM_VERSION_MINOR)
        if not versionOK:
            logging.error("Old EDAM version")
            return tools.exit()

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
        out.preloader.setMessage("Connect to Evernote...")
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
        out.showUser(info, True)



class Notebooks(GeekNoteConnector):
    """ Work with auth Notebooks """

    def list(self):
        result = self.getEvernote().findNotebooks()
        out.printList(result)

    def create(self, title):
        self.connectToEvertone()
        out.preloader.setMessage("Creating notebook...")
        result = self.getEvernote().createNotebook(name=title)

        if result:
            out.successMessage("notebook successfully created")
        else:
            out.failureMessage("Error while creating the note")
            return tools.exit()

        return result

    def edit(self, notebook, title):

        notebook = self._searchNotebook(notebook)

        out.preloader.setMessage("Updating notebook...")
        result = self.getEvernote().updateNotebook(guid=notebook.guid, name=title)

        if result:
            out.successMessage("notebook successfully updated")
        else:
            out.failureMessage("Error while creating the note")
            return tools.exit()

    def remove(self, notebook, force=None):

        notebook = self._searchNotebook(notebook)

        if not force and not out.confirm('Are you sure you want to delete this notebook: "%s"' % notebook.name):
            return tools.exit()

        out.preloader.setMessage("Deleting notebook...")
        result = self.getEvernote().deleteNotebook(guid=notebook.guid)

        if result:
            out.successMessage("notebook successfully updated")
        else:
            out.failureMessage("Error while creating the note")

    def _searchNotebook(self, notebook):

        result = self.getEvernote().findNotebooks()
        notebook = [item for item in result if item.name == notebook]

        if notebook:
            notebook = notebook[0]

        else:
            notebook = out.SelectSearchResult(result)

        logging.debug("Selected notebook: %s" % str(notebook))
        return notebook

    def getNoteGUID(self, notebook):
        if len(notebook) == 36 and notebook.find("-") == 4:
            return notebook

        result = self.getEvernote().findNotebooks()
        notebook = [item for item in result if item.name == notebook]
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

    def create(self, title, body, tags=None, notebook=None):

        self.connectToEvertone()

        inputData = self._parceInput(title, body, tags, notebook)

        out.preloader.setMessage("Creating note...")
        result = self.getEvernote().createNote(**inputData)

        if result:
            out.successMessage("Note successfully created")
        else:
            out.failureMessage("Error while creating the note")

    def edit(self, note, title=None, body=None, tags=None, notebook=None):

        self.connectToEvertone()
        note = self._searchNote(note)

        inputData = self._parceInput(title, body, tags, notebook, note)
        
        out.preloader.setMessage("Saving note...")
        result = self.getEvernote().updateNote(guid=note.guid, **inputData)

        if result:
            out.successMessage("Note successfully saved")
        else:
            out.failureMessage("Error while saving the note")

    def remove(self, note, force=None):

        self.connectToEvertone()
        note = self._searchNote(note)

        if not force and not out.confirm('Are you sure you want to delete this note: "%s"' % note.title):
            return tools.exit()

        out.preloader.setMessage("Deleting note...")
        result = self.getEvernote().deleteNote(note.guid)

        if result:
            out.successMessage("Note successful deleted")
        else:
            out.failureMessage("Error while deleting the note")

    def show(self, note):

        self.connectToEvertone()

        note = self._searchNote(note)

        out.preloader.setMessage("Loading note...")
        self.getEvernote().loadNoteContent(note)

        out.showNote(note)

    def _parceInput(self, title=None, body=None, tags=None, notebook=None, note=None):
        result = {
            "title": title,
            "body": body,
            "tags": tags,
            "notebook": notebook,
        }

        if body:
            if body == "WRITE_IN_EDITOR":
                logging.debug("launch system editor")
                if note:
                    self.getEvernote().loadNoteContent(note)
                    body = editor.edit(note.content)
                else:
                   body = editor.edit()
                result['body'] = editor.textToENML(body)

            else:
                if isinstance(body, str) and os.path.isfile(body):
                    logging.debug("Load body file")
                    body = open(body, "r").read()

                logging.debug("Convert body")
                result['body'] = editor.textToENML(body)

        if tags:
            result['tags'] = tools.strip(tags.split(','))

        if notebook:
            notepadGuid = Notebooks().getNoteGUID(notebook)
            if notepadGuid is None:
                newNotepad = Notebooks().create(notebook)
                notepadGuid = newNotepad.guid
            
            result['notebook'] = notepadGuid
            logging.debug("Search notebook")

        return result

    def _searchNote(self, note):
        note = tools.strip(note)
        if tools.checkIsInt(note):
            # TODO request in storage
            # TMP >>>
            result = self.getEvernote().findNotes(None, 1)
            note = result.notes[0]
            # TMP <<<

        else:
            request = self._createSearchRequest(search=note)
            
            logging.debug("Search notes: %s" % request)
            result = self.getEvernote().findNotes(request, 20)

            logging.debug("Search notes result: %s" % str(result))
            if result.totalNotes == 0:
                out.successMessage("Notes not found")
                return tools.exit()

            elif result.totalNotes == 1 or self.selectFirstOnUpdate:
                note = result.notes[0]

            else:
                logging.debug("Choose notes: %s" % str(result.notes)) 
                note = out.SelectSearchResult(result.notes)

        logging.debug("Selected note: %s" % str(note))
        return note


    def find(self, search=None, tags=None, notebooks=None, date=None, exact_entry=None, content_search=None, url_only=None, count=None, ):

        request = self._createSearchRequest(search, tags, notebooks, date, exact_entry, content_search)

        if not count:
            count = 20
        else:
            count = int(count)

        logging.debug("Search count: %s", count)

        result = self.getEvernote().findNotes(request, count)

        if result.totalNotes == 0:
            out.successMessage("Notes not found")

        # TODO Save result to storage
        out.SearchResult(result.notes, request)

    def _createSearchRequest(self, search=None, tags=None, notebooks=None, date=None, exact_entry=None, content_search=None):

        request = ""
        if search:
            search = tools.strip(search)
            if exact_entry or self.findExactOnUpdate:
                search = '"%s"' % search

            if content_search:
                request += "any:%s " % search 
            else:
                request += "intitle:%s " % search

        if tags:
            for tag in tools.strip(tags.split(',')):

                if tag.startswith('-'):
                    request +='-tag:"%s" ' % tag[1:]
                else:
                    request +='tag:"%s" ' % tag

        if date:
            date = tools.strip(date.split('-'))
            try:
                start_date =  time.strptime(date[0], "%d.%m.%Y")
                request +='created:"%s" ' % time.strftime("%Y%m%d", start_date)

                if len(date) == 2:
                    request += '-created:"%s" ' % time.strftime("%Y%m%d", time.strptime(date[1], "%d.%m.%Y"))
                else:
                    request += '-created:"%s" ' % time.strftime("%Y%m%d", time.gmtime(time.mktime(start_date)+60*60*24*2))

            except ValueError, e:
                out.failureMessage('Incorrect date format in --date attribute. Format: %s' % time.strftime("%d.%m.%Y", time.strptime('19991231', "%Y%m%d")))
                return tools.exit()

        if notebooks:
            for notebook in tools.strip(notebooks.split(',')):
                if notebook.startswith('-'):
                    request += '-notebook:"%s" ' % tools.strip(notebook[1:])
                else:
                    request += 'notebook:"%s" ' % tools.strip(notebook)

        logging.debug("Search request: %s", request)
        return request

def main():
    sys_argv = sys.argv[1:]

    COMAND = sys_argv[0] if len(sys.argv) >= 1 else ""

    # run check & run autocomplete
    if COMAND == "autocomplete":
        aparser = argparser(sys_argv[1:])
        aparser.printAutocomplete()
        return tools.exit()

    aparser = argparser(sys_argv)
    ARGS = aparser.parse()

    # error or help
    if not ARGS:
        return tools.exit()

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
    if COMAND == 'list-notebook':
        Notebooks().list(**ARGS)

    if COMAND == 'create-notebook':
        Notebooks().create(**ARGS)

    if COMAND == 'edit-notebook':
        Notebooks().edit(**ARGS)

    if COMAND == 'remove-notebook':
        Notebooks().remove(**ARGS)

if __name__ == "__main__":
    main()