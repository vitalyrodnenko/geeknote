# -*- coding: utf-8 -*-
from log import logging

def checkIsInt(value):
    try: 
        int(value)
        return True
    except ValueError:
        return False

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

def strip(data):
    if not data:
        return data

    if isinstance(data, dict):
        return dict([ [key.strip(' \t\n\r\"\''), val ] for key, val in data.iteritems() ])

    if isinstance(data, list):
        return map(lambda val: val.strip(' \t\n\r\"\''), data)

    if isinstance(data, str):
        return data.strip(' \t\n\r\"\'')
    
    raise Exception("Unexpected args type: %s. Expect list or dict" % type(data))

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

def printAutocomplete(COMMANDS, input):
    """
    COMMANDS is dictionary with structure:
    commad : {
        arguments : {
            argument: dict_with_info
        }
    }
    """
    def printGrid(list):
        print " ".join(list)

    level = len(input)

    #список команд
    CMD_LIST = COMMANDS.keys()
    # введенная команда
    CMD = None if level == 0 else input[0]
    # список возможных аргументов введенной команды
    ARGS =  COMMANDS[CMD]['arguments'].keys() if level > 0 and COMMANDS.has_key(CMD) and COMMANDS[CMD].has_key('arguments') else []
    # список введенных аргументов и их значений
    INP = [] if level <= 1 else input[1:]

    # список введенных аргументов (без значений)
    INP_ARGS = INP[::2] if INP else []
    # последний введенный аргумент
    INP_ARG = INP[-1] if len(INP)%2 == 1 else ( INP[-2] if INP else None )
    # последнее веденное значение
    INP_VAL = INP[-1] if INP and len(INP)%2 == 0 else None

    logging.debug("CMD_LIST : %s", str(CMD_LIST))
    logging.debug("CMD: %s", str(CMD))
    logging.debug("ARGS : %s", str(ARGS))
    logging.debug("INP : %s", str(INP))
    logging.debug("INP_ARGS : %s", str(INP_ARGS))
    logging.debug("INP_ARG : %s", str(INP_ARG))
    logging.debug("INP_VAL : %s", str(INP_VAL))

    # печатаем корневые команды
    if level == 0:
        printGrid(CMD_LIST)

    # работа с корневыми командами
    elif level == 1:

        # печатаем аргументы если команда найдена
        if CMD in CMD_LIST:
            printGrid(ARGS)

        # автозаполнение для неполной команды
        else:
            # фильтруем команды подходящие под введенный шаблон
            printGrid([item for item in CMD_LIST if item.startswith(CMD)])

    # обработка аргументов
    else:

        if INP_VAL:
            # фильтруем аргументы которые еще не ввели
            printGrid([item for item in ARGS if item not in INP_ARGS])

        else:
            # автозаполнение для неполной команды
            if INP_ARG not in ARGS:
                printGrid([item for item in ARGS if item not in INP_ARGS and item.startswith(INP_ARG)])

            # обработка аргумента
            else:
                print "" #"Please_input_%s" % INP_ARG.replace('-', '')