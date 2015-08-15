# -*- coding: utf-8 -*-

import getpass
import threading
import thread
import time
import datetime
import sys

import tools
from editor import Editor
import config


def preloaderPause(fn, *args, **kwargs):
    def wrapped(*args, **kwargs):

        if not preloader.isLaunch:
            return fn(*args, **kwargs)

        preloader.stop()
        result = fn(*args, **kwargs)
        preloader.launch()

        return result

    return wrapped


def preloaderStop(fn, *args, **kwargs):
    def wrapped(*args, **kwargs):

        if not preloader.isLaunch:
            return fn(*args, **kwargs)

        preloader.stop()
        result = fn(*args, **kwargs)
        return result

    return wrapped


class preloader(object):

    progress = (">  ", ">> ", ">>>", " >>", "  >", "   ")
    clearLine = "\r" + " " * 40 + "\r"
    message = None
    isLaunch = False
    counter = 0

    @staticmethod
    def setMessage(message, needLaunch=True):
        preloader.message = message
        if not preloader.isLaunch and needLaunch:
            preloader.launch()

    @staticmethod
    def launch():
        if not config.IS_OUT_TERMINAL:
            return
        preloader.counter = 0
        preloader.isLaunch = True
        thread.start_new_thread(preloader.draw, ())

    @staticmethod
    def stop():
        if not config.IS_OUT_TERMINAL:
            return
        preloader.counter = -1
        printLine(preloader.clearLine, "")
        preloader.isLaunch = False

    @staticmethod
    def exit(code=0):
        preloader.stop()

        if threading.current_thread().__class__.__name__ == '_MainThread':
            sys.exit(code)
        else:
            thread.exit()

    @staticmethod
    def draw():
        try:
            if not preloader.isLaunch:
                return

            while preloader.counter >= 0:
                printLine(preloader.clearLine, "")
                preloader.counter += 1
                printLine("%s : %s" % (preloader.progress[preloader.counter % len(preloader.progress)], preloader.message), "")

                time.sleep(0.3)
        except:
            pass


@preloaderPause
def GetUserCredentials():
    """Prompts the user for a username and password."""
    try:
        login = None
        password = None
        if login is None:
            login = rawInput("Login: ")

        if password is None:
            password = rawInput("Password: ", True)
    except (KeyboardInterrupt, SystemExit), e:
        if e.message:
            tools.exit(e.message)
        else:
            tools.exit

    return (login, password)

@preloaderPause
def GetUserAuthCode():
    """Prompts the user for a two factor auth code."""
    try:
        code = None
        if code is None:
          code = rawInput("Two-Factor Authentication Code: ")
    except (KeyboardInterrupt, SystemExit), e:
        if e.message:
            tools.exit(e.message)
        else:
            tools.exit

    return code

@preloaderStop
def SearchResult(listItems, request, **kwargs):
    """Print search results."""
    printLine("Search request: %s" % request)
    printList(listItems, **kwargs)


@preloaderStop
def SelectSearchResult(listItems, **kwargs):
    """Select a search result."""
    return printList(listItems, showSelector=True, **kwargs)


@preloaderStop
def confirm(message):
    printLine(message)
    try:
        while True:
            answer = rawInput("Yes/No: ")
            if answer.lower() in ["yes", "ye", "y"]:
                return True
            if answer.lower() in ["no", "n"]:
                return False
            failureMessage('Incorrect answer "%s", '
                           'please try again:\n' % answer)
    except (KeyboardInterrupt, SystemExit), e:
        if e.message:
            tools.exit(e.message)
        else:
            tools.exit


@preloaderStop
def showNote(note):
    separator("#", "TITLE")
    printLine(note.title)
    separator("=", "META")
    printLine("Created: %s" %
              (printDate(note.created).ljust(15, " ")))
    printLine("Updated: %s" %
              (printDate(note.updated).ljust(15, " ")))
    for key, value in note.attributes.__dict__.items():
        if value:
          printLine("%s: %s" % (key, value))
    separator("-", "CONTENT")
    if note.tagNames:
        printLine("Tags: %s" % ', '.join(note.tagNames))

    printLine(Editor.ENMLtoText(note.content))

@preloaderStop
def showNoteRaw(note):
    printLine(Editor.ENMLtoText(note.content, 'pre'))

@preloaderStop
def showUser(user, fullInfo):
    def line(key, value):
        if value:
            printLine("%s : %s" % (key.ljust(16, " "), value))

    separator("#", "USER INFO")
    line('Username', user.username)
    line('Name', user.name)
    line('Email', user.email)

    if fullInfo:
        limit = (int(user.accounting.uploadLimit) / 1024 / 1024)
        endlimit = time.gmtime(user.accounting.uploadLimitEnd / 1000)
        line('Upload limit', "%.2f" % limit)
        line('Upload limit end', time.strftime("%d.%m.%Y", endlimit))


@preloaderStop
def successMessage(message):
    """ Displaying a message. """
    printLine(message, "\n")


@preloaderStop
def failureMessage(message):
    """ Displaying a message."""
    printLine(message, "\n", sys.stderr)

def separator(symbol="", title=""):
    size = 40
    if title:
        sw = (size - len(title) + 2) / 2
        printLine("%s %s %s" % (symbol * sw,
                                title,
                                symbol * (sw - (len(title) + 1) % 2)))

    else:
        printLine(symbol * size + "\n")


@preloaderStop
def printList(listItems, title="", showSelector=False,
              showByStep=20, showUrl=False):

    if title:
        separator("=", title)

    total = len(listItems)
    printLine("Total found: %d" % total)
    for key, item in enumerate(listItems):
        key += 1

        printLine("%s : %s%s%s" % (
            str(key).rjust(3, " "),
            printDate(item.created).ljust(18, " ") if hasattr(item, 'created') else '',
            item.title if hasattr(item, 'title') else item.name,
            " " + (">>> " + config.NOTE_URL % item.guid) if showUrl else '',))

        if key % showByStep == 0 and key < total:
            printLine("-- More --", "\r")
            tools.getch()
            printLine(" " * 12, "\r")

    if showSelector:
        printLine("  0 : -Cancel-")
        try:
            while True:
                num = rawInput(": ")
                if tools.checkIsInt(num) and 1 <= int(num) <= total:
                    return listItems[int(num) - 1]
                if num == '0':
                    exit(1)
                failureMessage('Incorrect number "%s", '
                               'please try again:\n' % num)
        except (KeyboardInterrupt, SystemExit), e:
            if e.message:
                tools.exit(e.message)
            else:
                tools.exit


def rawInput(message, isPass=False):
    if isPass:
        data = getpass.getpass(message)
    else:
        data = raw_input(message)
    return tools.stdinEncode(data)


def printDate(timestamp):

    # Author @ash-2000 https://github.com/ash-2000
    # Check for crashing when timestamp is 13 digits on python2.7
    # pull request #260
    
    if len(str(timestamp)) == 13:
        timestamp = int(str(timestamp)[0:-3])

    # ---
    
    return datetime.date.strftime(datetime.date.fromtimestamp(timestamp), "%d.%m.%Y")

def printLine(line, endLine="\n", out=sys.stdout):
    message = line + endLine
    message = tools.stdoutEncode(message)
    try:
        out.write(message)
    except:
        pass
    out.flush()


def printAbout():
    printLine('Version: %s' % str(config.VERSION))
    printLine('Geeknote - a command line client for Evernote.')
    printLine('Use geeknote --help to read documentation.')
    printLine('And visit www.geeknote.me to check for updates.')
