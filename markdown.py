# -*- coding: utf-8 -*-

class textMarkup(object):
    """
    при инициализации передаем заметку из evernote
    """
    def __init__(self, text=""):
        import tempfile
        import os
        from subprocess import call
        from xml.dom.minidom import DOMImplementation
        import html2text
        import markdown

        pass

    """
    тут запускается парсер, который переводит
    текст заметки в читаьельный для баша формат
    """
    def view(self):
        pass

    """
    тут запускается редактор и после редактирования
    возвращается строка для записи в evernote
    """

    """
    ###########################################################################
    """
    def edit(self):
        pass

    def _convertToHTML(self, note):
        noteHTML = markdown.markdown(note)
        return noteHTML

    def _parseNoteToMarkDown(self, note):    
        txt = html2text.html2text(note.decode('us-ascii','ignore'))
        return txt.decode('utf-8', 'replace')

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
        contents = file.read()
        try:
            # Try to submit changes.
            noteContent = self._wrapNotetoHTML(contents)
            note.content = noteContent
            self.noteStore.updateNote(self.authToken, note)
        except:
            # If it's an error.
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


=======
import tempfile
import os
from subprocess import call
import html2text
import markdown
import md5
from tools import confirm
>>>>>>> origin/master

=======
    def _convertToHTML(self, note):
        note = unicode(note,"utf-8")
        noteHTML = markdown.markdown(note)
        return noteHTML.encode("utf-8")

    def _parseNoteToMarkDown(self, note):
        note = note.decode('utf-8')
        txt = html2text.html2text(note)
        return txt.encode('utf-8')
>>>>>>> origin/master

=======
        # ВНИМАНИЕ: Следующую строку надо переделать. Сейчас требуется передавать 2 аргумента функции, второй ничего не делает. Когда переделается метод, надо исправить этот кусок.
        note = self.getNote(noteid, noteid)
>>>>>>> origin/master

=======
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
>>>>>>> origin/master