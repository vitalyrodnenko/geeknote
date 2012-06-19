# -*- coding: utf-8 -*-
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EVERNOTE_SDK = os.path.join(PROJECT_ROOT, 'lib')
sys.path.append( EVERNOTE_SDK )

import tempfile
import html2text
import markdown
from tools import confirm

def ENMLtoText(contentENML):
    contentENML = contentENML.decode('utf-8')
    content = html2text.html2text(contentENML)
    return content.encode('utf-8')

def textToENML(content):
    """
    Create an ENML format of note.
    """
    if not isinstance(content, str):
        content = ""
    
    content = unicode(content,"utf-8")
    contentENML = markdown.markdown(content).encode("utf-8")

    body =  '<?xml version="1.0" encoding="UTF-8"?>'
    body += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
    body += '<en-note>%s</en-note>' % contentENML
    return body

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
    editor = os.environ.get("editor")
    if not (editor):
        editor = os.environ.get("EDITOR")
    if not (editor):
        # If default editor is not finded, then use nano as a default.
        editor = "nano"
    
    # Make a system call to open file for editing.
    os.system(editor + " " + tmpFileName)

    newContent =  open(tmpFileName, 'r').read()

    return textToENML(newContent)