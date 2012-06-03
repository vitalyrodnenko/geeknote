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
import locale
import time

import io
from oauth import GeekNoteAuth
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

        noteStoreUrl = self.userStore.getNoteStoreUrl(self.authToken)
        noteStoreHttpClient = THttpClient.THttpClient(noteStoreUrl)
        noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
        self.noteStore = NoteStore.Client(noteStoreProtocol)

    def findNotes(self, keywords, count):
        if not self.noteStore:
            self.getNoteStore()

        nf = NoteStore.NoteFilter()
        if keywords:
            nf.words = keywords
        return self.noteStore.findNotes(self.authToken, nf, 0, count)

    def getNote(self, name, full):
        notelist = self.findNotes(10,name)
        #for note in notelist.notes:
        if (len(notelist.notes) == 0):
            return None
        notelist.notes[0].content = self.noteStore.getNoteContent(self.authToken, notelist.notes[0].guid)
        return notelist.notes[0]

    def createNote(self, title, content, tags=None, notebook=None):
        if not self.noteStore:
            self.getNoteStore()

        note = Types.Note()
        note.title = title
        note.content = content

        if tags:
            note.tagNames = tags

        if notebook:
            note.notebookGuid = notebook

        logging.debug("New note : %s", note)

        try: 
            self.noteStore.createNote(self.authToken, note)
            return True
        except Exception, e:
            logging.error("Error: %s", str(e))
            return False

    def updateNote(self, guid, title=None, content=None, tags=None, notebook=None):
        if not self.noteStore:
            self.getNoteStore()

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
            self.noteStore.updateNote(self.authToken, note)
            return True
        except Exception, e:
            logging.error("Error: %s", str(e))
            return False

    def deleteNote(self, guid):
        if not self.noteStore:
            self.getNoteStore()

        logging.debug("Delete note with guid: %s", guid)
        try: 
            self.noteStore.deleteNote(self.authToken, guid)
            return True
        except Exception, e:
            logging.error("Error: %s", str(e))
            return False


class Notes(object):
    """Работа с заметками"""
    evernote = None
    
    def connectToEvertone(self):
        if self.evernote:
            return

        io.preloader.setMessage("Connect to Evernote...")

        self.evernote = GeekNote()
        return self
    
    def create(self, title, body, tags=None, notepad=None):

        if body == "WRITE_IN_EDITOR":
            # TODO launch editor
            logging.debug("launch system editor")

        # TMP >>>
        if body and not body.startswith("<?xml"):
            content = body
            body =  '<?xml version="1.0" encoding="UTF-8"?>'
            body += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            body += '<en-note>%s</en-note>' % content
        # TMP <<<

        if tags:
            tags = tools.strip(tags.split(','))

        if notepad:
            # TODO search notebooks in storage
            logging.debug("search notebook")

        self.connectToEvertone()
        io.preloader.setMessage("Creating note...")
        result = self.evernote.createNote(title=title, content=body, tags=tags, notebook=notepad)

        if result:
            io.successMessage("Note successfully created")
        else:
            io.failureMessage("Error while creating the note")

    def edit(self, note, title=None, body=None, tags=None, notepad=None):

        note = self._searchNote(note)

        if not title:
            title = note['title']
        
        if body == "WRITE_IN_EDITOR":
            # TODO launch editor
            logging.debug("launch system editor")

        # TMP >>>
        if body and not body.startswith("<?xml"):
            content = body
            body =  '<?xml version="1.0" encoding="UTF-8"?>'
            body += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            body += '<en-note>%s</en-note>' % content
        # TMP <<<

        if tags:
            tags = tools.strip(tags.split(','))

        if notepad:
            # TODO search notebooks in storage
            logging.debug("search notebook")

        self.connectToEvertone()
        io.preloader.setMessage("Saving note...")
        result = self.evernote.updateNote(guid=note['guid'], title=title, content=body, tags=tags, notebook=notepad)

        if result:
            io.successMessage("Note successfully saved")
        else:
            io.failureMessage("Error while saving the note")

    def remove(self, note):

        note = self._searchNote(note)

        if not io.removeConfirm(note['title']):
            exit(1)

        self.connectToEvertone()
        
        io.preloader.setMessage("Deleting note...")
        result = self.evernote.deleteNote(note['guid'])

        if result:
            io.successMessage("Note successful deleted")
        else:
            io.failureMessage("Error while deleting the note")

    def _searchNote(self, note):
        note = tools.strip(note)
        if tools.checkIsInt(note):
            # TODO request in storage
            # TMP >>>
            result = self._search(1)
            note = result.notes[0]
            # TMP <<<

        else:
            request = "intitle:%s" % note if note else None
            logging.debug("Search notes: %s" % request)
            result = self._search(20, request)

            logging.debug("Search notes result: %s" % str(result))
            if result.totalNotes == 0:
                io.successMessage("Notes not found")
                exit(1)

            elif result.totalNotes == 1:
                note = result.notes[0]

            else:
                notes = dict( (index+1, {"title": item.title, "guid": item.guid}) for index, item in enumerate(result.notes) )
                logging.debug("Choose notes: %s" % str(notes)) 
                note = io.SelectSearchResult(notes)

        logging.debug("Found notes: %s" % str(note))
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
        
        result = self._search(count, request)

        if result.totalNotes == 0:
            io.successMessage("Notes not found")

        notes = dict( (index+1, {"title": item.title, "guid": item.guid}) for index, item in enumerate(result.notes) )
        # TODO Save result to storage

        # print results
        io.SearchResult(notes, request)

    def _search(self, request, count):
        self.connectToEvertone()
        return self.evernote.findNotes(count, request)

COMMANDS = {
    "create": {
        "help": "Create note",
        "arguments": {
            "--title": {"help": "Set note title", "required": True},
            "--body": {"help": "Set note content", "required": True},
            "--tags": {"help": "Add tag to note"},
            "--notepad": {"help": "Add location marker to note"}
        }
    },
    "edit": {
        "help": "Create note",
        "arguments": {
            "--note": {"help": "Set note title"},
            "--title": {"help": "Set note title"},
            "--body": {"help": "Set note content"},
            "--tags": {"help": "Add tag to note"},
            "--notepad": {"help": "Add location marker to note"}
        }
    },
    "remove": {
        "help": "Create note",
        "arguments": {
            "--note": {"help": "Set note title"},
        }
    },
    "find": {
        "help": "Create note",
        "arguments": {
            "--search": {"help": "Add tag to note"},
            "--tags": {"help": "Add tag to note"},
            "--notepads": {"help": "Add location marker to note"},
            "--date": {"help": "Add location marker to note"},
            "--count": {"help": "Add location marker to note"},
        },
        "flags": {
            "--exact-entry": {"help": "Add tag to note", "action": "store_true"},
            "--content-search": {"help": "Add tag to note", "action": "store_true"},
            "--url-only": {"help": "Add tag to note"},
        }
    },
}

if __name__ == "__main__":

    COMAND = sys.argv[1] if len(sys.argv) >= 2 else ""

    # run check & run autocomplete
    if COMAND == "autocomplete":
        tools.printAutocomplete(COMMANDS, sys.argv[2:])
        exit(1)

    # create CLI parcer
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help="List of commands")

    for command, options in COMMANDS.iteritems():
        sub_parcer = subparsers.add_parser(command, help=options["help"])

        if options.has_key("arguments"):
            for argument, arg_options in options["arguments"].iteritems():
                sub_parcer.add_argument(argument, **arg_options)
        
        if options.has_key("flags"):
            for argument, arg_options in options["flags"].iteritems():
                sub_parcer.add_argument(argument, **arg_options)
    
    ARGS = dict(parser.parse_args()._get_kwargs())
    ARGS = tools.strip(ARGS)
    logging.debug("CLI options: %s", str(ARGS))
    
    if COMAND == 'create':
        Notes().create(**ARGS)

    if COMAND == 'edit':
        Notes().edit(**ARGS)

    if COMAND == 'remove':
        Notes().remove(**ARGS)

    if COMAND == 'find':
        Notes().find(**ARGS)
