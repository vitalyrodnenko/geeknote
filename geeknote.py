#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
import traceback

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append( os.path.join(PROJECT_ROOT, 'lib') )

import config

import hashlib
import binascii
import time
from datetime import datetime
from urlparse import urlparse
import re
import lib.thrift.protocol.TBinaryProtocol as TBinaryProtocol
import lib.thrift.transport.THttpClient as THttpClient
import lib.evernote.edam.userstore.UserStore as UserStore
import lib.evernote.edam.userstore.constants as UserStoreConstants
import lib.evernote.edam.notestore.NoteStore as NoteStore
import lib.evernote.edam.type.ttypes as Types
import lib.evernote.edam.error.ttypes as Errors

import locale
import time
import signal

import out
from argparser import argparser

from oauth import GeekNoteAuth

from storage import Storage
import editor
import tools
from log import logging


# decorator to disable evernote connection on create instance of GeekNote
def GeekNoneDBConnectOnly(func):
    def wrapper(*args, **kwargs):
        GeekNote.skipInitConnection = True
        return func(*args, **kwargs)
    return wrapper

class GeekNote(object):

    userStoreUri = config.USER_STORE_URI
    consumerKey = config.CONSUMER_KEY
    consumerSecret = config.CONSUMER_SECRET
    authToken = None
    userStore = None
    noteStore = None
    storage = None
    skipInitConnection = False

    def __init__(self, skipInitConnection=False):
        if skipInitConnection:
            self.skipInitConnection = True

        self.getStorage()

        if self.skipInitConnection is True:
            return

        self.getUserStore()

        if not self.checkAuth():
            self.auth()

    def EdamException(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception, e:
                logging.error("Error: %s : %s", func.__name__, str(e))

                if not hasattr(e, 'errorCode'):
                    out.failureMessage("Sorry, operation has failed!!!.")
                    tools.exit()

                errorCode = int(e.errorCode)

                # auth-token error, re-auth
                if errorCode == 9:
                    storage = Storage()
                    storage.removeUser()
                    GeekNote()
                    return func(*args, **kwargs)

                elif errorCode == 3:
                    out.failureMessage("Sorry, you do not have permissions to do this operation.")

                else:
                    return False

                tools.exit()

        return wrapper

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
    
        self.checkVersion()

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
            return True
        return False

    def auth(self):
        GNA = GeekNoteAuth()
        self.authToken = GNA.getToken()
        userInfo = self.getUserInfo()
        if not isinstance(userInfo, object):
            logging.error("User info not get")
            return False

        self.getStorage().createUser(self.authToken, userInfo)
        return True

    def getUserInfo(self):
        return self.getUserStore().getUser(self.authToken)

    def removeUser(self):
        return self.getStorage().removeUser()
    
    """
    WORK WITH NOTEST
    """
    @EdamException
    def findNotes(self, keywords, count, createOrder=False):
        
        noteFilter = NoteStore.NoteFilter(order=Types.NoteSortOrder.RELEVANCE)
        if createOrder:
            noteFilter.order = Types.NoteSortOrder.CREATED

        if keywords:
            noteFilter.words = keywords
        return self.getNoteStore().findNotes(self.authToken, noteFilter, 0, count)

    @EdamException
    def loadNoteContent(self, note):
        """ modify Note object """
        if not isinstance(note, object):
            raise Exception("Note content must be an instanse of Note, '%s' given." % type(note))

        note.content = self.getNoteStore().getNoteContent(self.authToken, note.guid)
        # fill the tags in
        if note.tagGuids and not note.tagNames:
          note.tagNames = [];
          for guid in note.tagGuids:
            tag = self.getNoteStore().getTag(self.authToken,guid)
            note.tagNames.append(tag.name)

    @EdamException
    def createNote(self, title, content, tags=None, notebook=None, created=None):
        note = Types.Note()
        note.title = title
        note.content = content
        note.created = created

        if tags:
            note.tagNames = tags

        if notebook:
            note.notebookGuid = notebook

        logging.debug("New note : %s", note)

        self.getNoteStore().createNote(self.authToken, note)
        return True

    @EdamException
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

        self.getNoteStore().updateNote(self.authToken, note)
        return True

    @EdamException
    def removeNote(self, guid):
        logging.debug("Delete note with guid: %s", guid)

        self.getNoteStore().deleteNote(self.authToken, guid)
        return True

    """
    WORK WITH NOTEBOOKS
    """
    @EdamException
    def findNotebooks(self):
        return self.getNoteStore().listNotebooks(self.authToken)

    @EdamException
    def createNotebook(self, name):
        notebook = Types.Notebook()
        notebook.name = name

        logging.debug("New notebook : %s", notebook)

        result = self.getNoteStore().createNotebook(self.authToken, notebook)
        return result

    @EdamException
    def updateNotebook(self, guid, name):
        notebook = Types.Notebook()
        notebook.name = name
        notebook.guid = guid

        logging.debug("Update notebook : %s", notebook)

        self.getNoteStore().updateNotebook(self.authToken, notebook)
        return True

    @EdamException
    def removeNotebook(self, guid):
        logging.debug("Delete notebook : %s", guid)

        self.getNoteStore().expungeNotebook(self.authToken, guid)
        return True

    """
    WORK WITH TAGS
    """
    @EdamException
    def findTags(self):
        return self.getNoteStore().listTags(self.authToken)

    @EdamException
    def createTag(self, name):
        tag = Types.Tag()
        tag.name = name

        logging.debug("New tag : %s", tag)

        result = self.getNoteStore().createTag(self.authToken, tag)
        return result

    @EdamException
    def updateTag(self, guid, name):
        tag = Types.Tag()
        tag.name = name
        tag.guid = guid

        logging.debug("Update tag : %s", tag)

        self.getNoteStore().updateTag(self.authToken, tag)
        return True

    @EdamException
    def removeTag(self, guid):
        logging.debug("Delete tag : %s", guid)

        self.getNoteStore().expungeTag(self.authToken, guid)
        return True

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

    @GeekNoneDBConnectOnly
    def user(self, full=None):
        if not self.getEvernote().checkAuth():
            out.failureMessage("You not logged in.")
            return tools.exit()

        if full:
            info = self.getEvernote().getUserInfo()
        else:
            info = self.getStorage().getUserInfo()
        out.showUser(info, full)

    @GeekNoneDBConnectOnly
    def login(self):
        if self.getEvernote().checkAuth():
            out.successMessage("You have already logged in.")
            return tools.exit()

        if self.getEvernote().auth():
            out.successMessage("You have successfully logged in.")
        else:
            out.failureMessage("Login error.")
            return tools.exit()

    @GeekNoneDBConnectOnly
    def logout(self, force=None):
        if not self.getEvernote().checkAuth():
            out.successMessage("You have already logged out.")
            return tools.exit()

        if not force and not out.confirm('Are you sure you want to logout?'):
            return tools.exit()

        result = self.getEvernote().removeUser()
        if result:
            out.successMessage("You have successfully logged out.")
        else:
            out.failureMessage("Logout error.")
            return tools.exit()

    @GeekNoneDBConnectOnly
    def settings(self, editor=None):
        if editor:
            if editor == '#GET#':
                editor = self.getStorage().getUserprop('editor')
                if not editor:
                    editor = config.DEF_WIN_EDITOR if sys.platform == 'win32' else config.DEF_UNIX_EDITOR
                out.successMessage("Current editor is: %s" % editor)
            else:
                self.getStorage().setUserprop('editor', editor)
                out.successMessage("Changes have been saved.")

class Tags(GeekNoteConnector):
    """ Work with auth Notebooks """

    def list(self):
        result = self.getEvernote().findTags()
        out.printList(result)

    def create(self, title):
        self.connectToEvertone()
        out.preloader.setMessage("Creating tag...")
        result = self.getEvernote().createTag(name=title)

        if result:
            out.successMessage("Tag has been successfully created.")
        else:
            out.failureMessage("Error while the process of creating the tag.")
            return tools.exit()

        return result

    def edit(self, tagname, title):
        tag = self._searchTag(tagname)

        out.preloader.setMessage("Updating tag...")
        result = self.getEvernote().updateTag(guid=tag.guid, name=title)

        if result:
            out.successMessage("Tag has been successfully updated.")
        else:
            out.failureMessage("Error while the updating the tag.")
            return tools.exit()

    def remove(self, tagname, force=None):
        tag = self._searchTag(tagname)

        if not force and not out.confirm('Are you sure you want to delete this tag: "%s"?' % tag.name):
            return tools.exit()

        out.preloader.setMessage("Deleting tag...")
        result = self.getEvernote().removeTag(guid=tag.guid)

        if result:
            out.successMessage("Tag has been successfully removed.")
        else:
            out.failureMessage("Error while removing the tag.")

    def _searchTag(self, tag):
        result = self.getEvernote().findTags()
        tag = [item for item in result if item.name == tag]

        if tag:
            tag = tag[0]
        else:
            tag = out.SelectSearchResult(result)

        logging.debug("Selected tag: %s" % str(tag))
        return tag

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
            out.successMessage("Notebook has been successfully created.")
        else:
            out.failureMessage("Error while the process of creating the notebook.")
            return tools.exit()

        return result

    def edit(self, notebook, title):
        notebook = self._searchNotebook(notebook)

        out.preloader.setMessage("Updating notebook...")
        result = self.getEvernote().updateNotebook(guid=notebook.guid, name=title)

        if result:
            out.successMessage("Notebook has been successfully updated.")
        else:
            out.failureMessage("Error while the updating the notebook.")
            return tools.exit()

    def remove(self, notebook, force=None):
        notebook = self._searchNotebook(notebook)

        if not force and not out.confirm('Are you sure you want to delete this notebook: "%s"?' % notebook.name):
            return tools.exit()

        out.preloader.setMessage("Deleting notebook...")
        result = self.getEvernote().removeNotebook(guid=notebook.guid)

        if result:
            out.successMessage("Notebook has been successfully removed.")
        else:
            out.failureMessage("Error while removing the notebook.")

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

    def create(self, title, content, tags=None, notebook=None):

        self.connectToEvertone()

        inputData = self._parceInput(title, content, tags, notebook)

        out.preloader.setMessage("Creating note...")
        result = self.getEvernote().createNote(**inputData)

        if result:
            out.successMessage("Note has been successfully created.")
        else:
            out.failureMessage("Error while creating the note.")

    def edit(self, note, title=None, content=None, tags=None, notebook=None):

        self.connectToEvertone()
        note = self._searchNote(note)

        inputData = self._parceInput(title, content, tags, notebook, note)
        
        out.preloader.setMessage("Saving note...")
        result = self.getEvernote().updateNote(guid=note.guid, **inputData)

        if result:
            out.successMessage("Note has been successfully saved.")
        else:
            out.failureMessage("Error while saving the note.")

    def remove(self, note, force=None):

        self.connectToEvertone()
        note = self._searchNote(note)

        if not force and not out.confirm('Are you sure you want to delete this note: "%s"?' % note.title):
            return tools.exit()

        out.preloader.setMessage("Deleting note...")
        result = self.getEvernote().removeNote(note.guid)

        if result:
            out.successMessage("Note has been successful deleted.")
        else:
            out.failureMessage("Error while deleting the note.")

    def show(self, note):

        self.connectToEvertone()

        note = self._searchNote(note)
        
        out.preloader.setMessage("Loading note...")
        self.getEvernote().loadNoteContent(note)

        out.showNote(note)

    def _parceInput(self, title=None, content=None, tags=None, notebook=None, note=None):
        result = {
            "title": title,
            "content": content,
            "tags": tags,
            "notebook": notebook,
        }
        result = tools.strip(result)

        # if get note without params
        if note and title is None and content is None and tags is None and notebook is None:
            content = config.EDITOR_OPEN

        if title is None and note:
            result['title'] = note.title

        if content:
            if content == config.EDITOR_OPEN:
                logging.debug("launch system editor")
                if note:
                    self.getEvernote().loadNoteContent(note)
                    content = editor.edit(note.content)
                else:
                   content = editor.edit()

            elif isinstance(content, str) and os.path.isfile(content):
                logging.debug("Load content from the file")
                content = open(content, "r").read()

            logging.debug("Convert content")
            content = editor.textToENML(content)

            result['content'] = content

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

        # load search result
        result = self.getStorage().getSearch()
        if result and tools.checkIsInt(note) and 1 <= int(note) <= len(result.notes):
            note = result.notes[int(note)-1]

        else:
            request = self._createSearchRequest(search=note)

            logging.debug("Search notes: %s" % request)
            result = self.getEvernote().findNotes(request, 20)

            logging.debug("Search notes result: %s" % str(result))
            if result.totalNotes == 0:
                out.successMessage("Notes have not been found.")
                return tools.exit()

            elif result.totalNotes == 1 or self.selectFirstOnUpdate:
                note = result.notes[0]

            else:
                logging.debug("Choose notes: %s" % str(result.notes)) 
                note = out.SelectSearchResult(result.notes)

        logging.debug("Selected note: %s" % str(note))
        return note


    def find(self, search=None, tags=None, notebooks=None, date=None, exact_entry=None, content_search=None, with_url=None, count=None, ):

        request = self._createSearchRequest(search, tags, notebooks, date, exact_entry, content_search)

        if not count:
            count = 20
        else:
            count = int(count)

        logging.debug("Search count: %s", count)

        createFilter = True if search == "*" else False
        result = self.getEvernote().findNotes(request, count, createFilter)

        if result.totalNotes == 0:
            out.successMessage("Notes have not been found.")

        # save search result
        # print result
        self.getStorage().setSearch(result)

        out.SearchResult(result.notes, request, showUrl=with_url)

    def _createSearchRequest(self, search=None, tags=None, notebooks=None, date=None, exact_entry=None, content_search=None):

        request = ""
        if notebooks:
            for notebook in tools.strip(notebooks.split(',')):
                if notebook.startswith('-'):
                    request += '-notebook:"%s" ' % tools.strip(notebook[1:])
                else:
                    request += 'notebook:"%s" ' % tools.strip(notebook)

        if tags:
            for tag in tools.strip(tags.split(',')):

                if tag.startswith('-'):
                    request +='-tag:"%s" ' % tag[1:]
                else:
                    request +='tag:"%s" ' % tag

        if date:
            date = tools.strip(date.split('-'))
            try:
                dateStruct = time.strptime(date[0]+" 00:00:00", "%d.%m.%Y %H:%M:%S")
                request +='created:%s ' % time.strftime("%Y%m%d", time.localtime(time.mktime(dateStruct)))
                if len(date) == 2:
                    dateStruct = time.strptime(date[1]+" 00:00:00", "%d.%m.%Y %H:%M:%S")
                request += '-created:%s ' % time.strftime("%Y%m%d", time.localtime(time.mktime(dateStruct)+60*60*24))
            except ValueError, e:
                out.failureMessage('Incorrect date format in --date attribute. Format: %s' % time.strftime("%d.%m.%Y", time.strptime('19991231', "%Y%m%d")))
                return tools.exit()

        if search:
            search = tools.strip(search)
            if exact_entry or self.findExactOnUpdate:
                search = '"%s"' % search

            if content_search:
                request += "%s" % search 
            else:
                request += "intitle:%s" % search

        logging.debug("Search request: %s", request)
        return request

# парсинг входного потока и подстановка аргументов
def modifyArgsByStdinStream():
    content = sys.stdin.read()
    content = tools.stdinEncode(content)

    if not content:
        out.failureMessage("Input stream is empty.")
        return tools.exit()

    title = ' '.join(content.split(' ', 5)[:-1])
    title = re.sub(r'(\r\n|\r|\n)', r' ', title)
    if not title:
        out.failureMessage("Error while crating title of note from stream.")
        return tools.exit()
    elif len(title) > 50:
        title = title[0:50] + '...'

    ARGS = {
        'title': title,
        'content': content
    }

    return ('create', ARGS)

def main(args=None):
    try:
        # if terminal
        if config.IS_IN_TERMINAL:
            sys_argv = sys.argv[1:]
            if isinstance(args, list):
                sys_argv = args

            sys_argv = tools.decodeArgs(sys_argv)

            COMMAND = sys_argv[0] if len(sys_argv) >= 1 else None

            aparser = argparser(sys_argv)
            ARGS = aparser.parse()

        # if input stream
        else:
            COMMAND, ARGS = modifyArgsByStdinStream()

        # error or help
        if COMMAND is None or ARGS is False:
            return tools.exit()

        logging.debug("CLI options: %s", str(ARGS))

        # Users
        if COMMAND == 'user':
            User().user(**ARGS)

        if COMMAND == 'login':
            User().login(**ARGS)

        if COMMAND == 'logout':
            User().logout(**ARGS)

        if COMMAND == 'settings':
            User().settings(**ARGS)

        # Notes
        if COMMAND == 'create':
            Notes().create(**ARGS)

        if COMMAND == 'edit':
            Notes().edit(**ARGS)

        if COMMAND == 'remove':
            Notes().remove(**ARGS)

        if COMMAND == 'show':
            Notes().show(**ARGS)

        if COMMAND == 'find':
            Notes().find(**ARGS)

        # Notebooks
        if COMMAND == 'notebook-list':
            Notebooks().list(**ARGS)

        if COMMAND == 'notebook-create':
            Notebooks().create(**ARGS)

        if COMMAND == 'notebook-edit':
            Notebooks().edit(**ARGS)

        if COMMAND == 'notebook-remove':
            Notebooks().remove(**ARGS)

        # Tags
        if COMMAND == 'tag-list':
            Tags().list(**ARGS)

        if COMMAND == 'tag-create':
            Tags().create(**ARGS)

        if COMMAND == 'tag-edit':
            Tags().edit(**ARGS)

        if COMMAND == 'tag-remove':
            Tags().remove(**ARGS)

    except (KeyboardInterrupt, SystemExit, tools.ExitException):
        pass

    except Exception, e:
        traceback.print_exc()
        logging.error("App error: %s", str(e))

    # перывание для preloader'а
    tools.exit()

if __name__ == "__main__":
    main()
