# -*- coding: utf-8 -*-

def getch():
    """
    Interrupting program until pressed any key
    """
    try:
        import msvcrt
        return msvcrt.getch()

    except ImportError:
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

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
