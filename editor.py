# -*- coding: utf-8 -*-

import os, sys

# path to libs in unix systems
sys.path.append( os.path.join('/', 'usr', 'local', 'lib', 'geeknone'))

import tempfile
import html2text
import markdown
import tools
import out
import sys
import os
import re
import config
from storage import Storage


def ENMLtoText(contentENML):
    contentENML = contentENML.decode('utf-8')
    content = html2text.html2text(contentENML)
    return content.encode('utf-8')

def wrapENML(contentHTML):
    body =  '<?xml version="1.0" encoding="UTF-8"?>\n'
    body += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">\n'
    body += '<en-note>%s</en-note>' % contentHTML
    return body

def textToENML(content):
    """
    Create an ENML format of note.
    """
    if not isinstance(content, str):
        content = ""
    try:
        content = unicode(content,"utf-8")
        content = re.sub(r'(\r|\n|\r\n)', r'  \1', content) # add 2 space for cteating br tags
        contentHTML = markdown.markdown(content).encode("utf-8")
    except:
        out.failureMessage("Error. Content must be an UTF-8 encode.")
        return None

    return wrapENML(contentHTML)

def edit(content=None):
    """
    Call the system editor, that types as a default in the system.
    Editing goes in markdown format, and then the markdown converts into HTML, before uploading to Evernote.
    """
    if content is None:
        content = ""

    if not isinstance(content, str):
        raise Exception("Note content must be an instanse of string, '%s' given." % type(content))

    (tmpFileHandler, tmpFileName) = tempfile.mkstemp()
    
    os.write(tmpFileHandler, ENMLtoText(content))
    os.close(tmpFileHandler)
    
    # Try to find default editor in the system.
    storage = Storage()
    editor = storage.getUserprop('editor')
    print editor
    if not editor:
        # If default editor is not finded, then use nano as a default.
        if sys.platform == 'win32':
            editor = config.DEF_WIN_EDITOR
        else:
            editor = config.DEF_UNIX_EDITOR

    if not editor:
        editor = os.environ.get("editor")

    if not editor:
        editor = os.environ.get("EDITOR")

    # Make a system call to open file for editing.
    os.system(editor + " " + tmpFileName)

    newContent =  open(tmpFileName, 'r').read()

    return newContent
