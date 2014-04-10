# -*- coding: utf-8 -*-

import os
import sys
import tempfile
from bs4 import BeautifulSoup
import threading
import hashlib
import html2text as html2text
import markdown2 as markdown
import tools
import out
import re
import config
from storage import Storage
from log import logging
from xml.sax.saxutils import escape, unescape

class EditorThread(threading.Thread):

    def __init__(self, editor):
        threading.Thread.__init__(self)
        self.editor = editor

    def run(self):
        self.editor.edit()


class Editor(object):
    # escape() and unescape() takes care of &, < and >.

    @staticmethod
    def getHtmlEscapeTable():
        return {'"': "&quot;",
                "'": "&apos;",
                '\n': "<br />"}

    @staticmethod
    def getHtmlUnescapeTable():
        return {v:k for k, v in Editor.getHtmlEscapeTable().items()}

    @staticmethod
    def HTMLEscape(text):
        return escape(text, Editor.getHtmlEscapeTable())

    @staticmethod
    def HTMLUnescape(text):
        return unescape(text, Editor.getHtmlUnescapeTable())

    @staticmethod
    def ENMLtoText(contentENML):
        html2text.BODY_WIDTH = 0
        soup = BeautifulSoup(contentENML.decode('utf-8'))

        for section in soup.select('li > p'):
            section.replace_with( section.contents[0] )

        for section in soup.select('li > br'):
            next_sibling = section.next_sibling.next_sibling
            if next_sibling:
                if next_sibling.find('li'):
                    section.extract()
            else:
                section.extract()

        content = html2text.html2text(soup.prettify())
        content = re.sub(r' *\n', os.linesep, content)
        return content.encode('utf-8')

    @staticmethod
    def wrapENML(contentHTML):
        body = '<?xml version="1.0" encoding="UTF-8"?>\n'\
           '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">\n'\
           '<en-note>%s</en-note>' % contentHTML
        return body

    @staticmethod
    def textToENML(content, raise_ex=False, format='markdown'):
        """
        Create an ENML format of note.
        """
        if not isinstance(content, str):
            content = ""
        try:
            content = unicode(content, "utf-8")
            # add 2 space before new line in paragraph for cteating br tags
            content = re.sub(r'([^\r\n])([\r\n])([^\r\n])', r'\1  \n\3', content)
            if format=='markdown':
              contentHTML = markdown.markdown(content).encode("utf-8")
              # Non-Pretty HTML output
              contentHTML = str(BeautifulSoup(contentHTML)) 
            else:
              contentHTML = self.HTMLEscape(content)
            return Editor.wrapENML(contentHTML)
        except:
            if raise_ex:
                raise Exception("Error while parsing text to html."
                                " Content must be an UTF-8 encode.")

            logging.error("Error while parsing text to html. "
                          "Content must be an UTF-8 encode.")
            out.failureMessage("Error while parsing text to html. "
                               "Content must be an UTF-8 encode.")
            return tools.exit()

    def __init__(self, content):
        if not isinstance(content, str):
            raise Exception("Note content must be an instanse "
                            "of string, '%s' given." % type(content))
            
        (tempfileHandler, tempfileName) = tempfile.mkstemp(suffix=".markdown")
        os.write(tempfileHandler, self.ENMLtoText(content))
        os.close(tempfileHandler)
        
        self.content = content
        self.tempfile = tempfileName

    def getTempfileChecksum(self):
        with open(self.tempfile, 'rb') as fileHandler:
            checksum = hashlib.md5()
            while True:
                data = fileHandler.read(8192)
                if not data:
                    break
                checksum.update(data)

            return checksum.hexdigest()

    def edit(self):
        """
        Call the system editor, that types as a default in the system.
        Editing goes in markdown format, and then the markdown
        converts into HTML, before uploading to Evernote.
        """

        # Try to find default editor in the system.
        storage = Storage()
        editor = storage.getUserprop('editor')

        if not editor:
            editor = os.environ.get("editor")

        if not editor:
            editor = os.environ.get("EDITOR")

        if not editor:
            # If default editor is not finded, then use nano as a default.
            if sys.platform == 'win32':
                editor = config.DEF_WIN_EDITOR
            else:
                editor = config.DEF_UNIX_EDITOR

        # Make a system call to open file for editing.
        logging.debug("launch system editor: %s %s" % (editor, self.tempfile))

        out.preloader.stop()
        os.system(editor + " " + self.tempfile)
        out.preloader.launch()
        newContent = open(self.tempfile, 'r').read()

        return newContent
