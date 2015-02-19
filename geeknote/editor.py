# -*- coding: utf-8 -*-

import os
import sys
import tempfile
from bs4 import BeautifulSoup, NavigableString
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
    def checklistInENMLtoSoup(soup):
        '''
        Transforms Evernote checklist elements to github `* [ ]` task list style
        '''
        transform_tags = ['p','div']

        # soup.select cant be used with dashes: https://bugs.launchpad.net/beautifulsoup/+bug/1276211
        for todo in soup.find_all('en-todo'):
            parent = todo.parent
            transform = parent.find() == todo and parent.name in transform_tags

            checked = todo.attrs.get('checked',None) == "true"
            todo.replace_with("[x] " if checked else "[ ] ")

            # EN checklist can appear anywhere, but if they appear at the beggining
            # of a block element, transform it so it ressembles github markdown syntax
            if transform:
                content = ''.join(unicode(child) for child in parent.children
                    if isinstance(child, NavigableString)
                ).strip()

                new_tag = soup.new_tag("li")
                new_tag.string = content
                parent.replace_with(new_tag)


    @staticmethod
    def ENMLtoText(contentENML):
        html2text.BODY_WIDTH = 0
        soup = BeautifulSoup(contentENML.decode('utf-8'))

        for section in soup.select('li > p'):
            section.replace_with( section.contents[0] )

        for section in soup.select('li > br'):
            if section.next_sibling:
                next_sibling = section.next_sibling.next_sibling
                if next_sibling:
                    if next_sibling.find('li'):
                        section.extract()
                else:
                    section.extract()

        Editor.checklistInENMLtoSoup(soup)

        for section in soup.findAll('en-todo', checked='true'):
            section.replace_with('[x]')

        for section in soup.findAll('en-todo'):
            section.replace_with('[ ]')

#       content = html2text.html2text(soup.prettify())
        content = html2text.html2text(str(soup).decode('utf-8'))

        content = re.sub(r' *\n', os.linesep, content)

        return content.encode('utf-8')

    @staticmethod
    def wrapENML(contentHTML):
        body = '<?xml version="1.0" encoding="UTF-8"?>\n'\
           '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">\n'\
           '<en-note>%s</en-note>' % contentHTML
        return body

    @staticmethod
    def checklistInSoupToENML(soup):
        '''
        Transforms github style checklists `* [ ]` in the BeautifulSoup tree to
        enml.
        '''

        checktodo_re = re.compile(r'\[(.)\]')

        # To be more github compatible, if in a list all elements begins with `[ ]``
        # transform it to normal `[ ]` evernote elements
        for ul in soup.find_all('ul'):
            tasks = []; istodo = True

            for li in ul.find_all('li'):
                task = soup.new_tag('div')
                todo_tag = soup.new_tag('en-todo')

                reg = checktodo_re.match(li.get_text())
                istodo = istodo and reg
                character = reg.group(1) if reg else None

                if character == "x": todo_tag['checked']="true"

                task.append(todo_tag)
                if reg: task.append(NavigableString(li.get_text()[3:].strip()))
                tasks.append(task)

            if istodo:
                for task in tasks: ul.insert_after(task)
                ul.extract()

        # For the rest of elements just replace `[ ]` with the appropriate element
        for todo in soup.find_all(text=checktodo_re):
            str_re = re.match(r'(.*)\[(.)\](.*)',todo)
            pre = str_re.group(1)
            post = str_re.group(3)

            todo_tag = soup.new_tag('en-todo')
            if str_re.group(2) == "x": todo_tag['checked']="true"

            todo.replace_with(todo_tag)
            todo_tag.insert_before(pre)
            todo_tag.insert_after(post)


    @staticmethod
    def textToENML(content, raise_ex=False, format='markdown'):
        """
        Create an ENML format of note.
        """
        if not isinstance(content, str):
            content = ""
        try:
            content = unicode(content, "utf-8")
            # add 2 space before new line in paragraph for creating br tags
            content = re.sub(r'([^\r\n])([\r\n])([^\r\n])', r'\1  \n\3', content)
            if format=='markdown':
              contentHTML = markdown.markdown(content)

              soup = BeautifulSoup(contentHTML, 'html.parser')
              Editor.checklistInSoupToENML(soup)

              # Non-Pretty HTML output
              contentHTML = str(soup)
            #
            # For the 'pre' format, simply wrap the content with a 'pre' tag. Do
            # perform any parsing/mutation.
            #
            elif format=='pre':
              contentHTML = u''.join(('<pre>', content, '</pre>')).encode("utf-8")
            else:
              contentHTML = Editor.HTMLEscape(content)

            contentHTML = contentHTML.replace('[x]','<en-todo checked="true"></en-todo>')
            contentHTML = contentHTML.replace('[ ]','<en-todo></en-todo>')

            return Editor.wrapENML(contentHTML)
        except:
            import traceback
            traceback.print_exc()
            if raise_ex:
                raise Exception("Error while parsing text to html."
                                " Content must be an UTF-8 encode.")

            logging.error("Error while parsing text to html. "
                          "Content must be an UTF-8 encode.")
            out.failureMessage("Error while parsing text to html. "
                               "Content must be an UTF-8 encode.")
            return tools.exitErr()

    def __init__(self, content):
        if not isinstance(content, str):
            raise Exception("Note content must be an instance "
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
