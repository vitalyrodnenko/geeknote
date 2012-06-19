# -*- coding: utf-8 -*-
import getpass
import time
import sys
import thread
import tools
import editor

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

    #progress = "\|/-"
    progress = (">  ", ">> ", ">>>", " >>", "  >", "   ")
    clearLine = "\r"+" "*40+"\r"
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
        preloader.counter = 0
        preloader.isLaunch = True
        thread.start_new_thread(preloader.draw, ())

    @staticmethod
    def stop():
        preloader.counter = -1
        preloader.draw()
        preloader.isLaunch = False

    @staticmethod
    def draw():
        if not preloader.isLaunch:
            return

        printLine(preloader.clearLine, "")
        if preloader.counter == -1:
            sys.stdout.flush()
            return

        preloader.counter += 1
        printLine("%s : %s" % (preloader.progress[preloader.counter % len(preloader.progress)], preloader.message), "")
        sys.stdout.flush()

        time.sleep(0.3)
        preloader.draw()

@preloaderPause
def GetUserCredentials():
    """Prompts the user for a username and password."""
    
    email = None
    password = None
    if email is None:
        email = raw_input("Email: ")
        
    if password is None:
        password = getpass.getpass("Password for %s: " % email)
    
    return (email, password)

@preloaderStop
def SearchResult(listItems, request):
    """Печать результатов поиска"""
    printLine("Search request: %s" % request)
    printList(listItems)


@preloaderStop
def SelectSearchResult(listItems):
    """Выбор результата поиска"""
    return printList(listItems, showSelector=True)


@preloaderStop
def confirm(message):
    printLine(message)
    sys.stdout.flush()
    while True:
        answer = raw_input("Yes/No: ")
        if answer.lower() in ["yes", "ye", "y"]:
            return True
        if answer.lower() in ["no", "n"]:
            return False
        failureMessage('Incorrect answer "%s", please try again:\n' % answer)

@preloaderStop
def showNote(note):

    separator("#", "TITLE")
    printLine(note.title)
    separator("=", "CONTENT")
    if note.tagNames:
        printLine("Tags: %s" % ', '.join(note.tagNames))

    printLine(editor.ENMLtoText(note.content))
    sys.stdout.flush()

@preloaderStop
def showUser(user, fullInfo):
    def line(key, value):
        if value:
            printLine("%s : %s" % (key.ljust(16, " "), value))

    separator("#", "USER INFO")
    line('Username', user.username)
    line('Name', user.name)
    line('eEail', user.email)

    if fullInfo:
        line('Upload limit', "%.2f" % (int(user.accounting.uploadLimit) / 1024 / 1024))
        line('Upload limit end', time.strftime("%d.%m.%Y", time.gmtime(user.accounting.uploadLimitEnd / 1000 )) )
    sys.stdout.flush()


@preloaderStop
def successMessage(message):
    """ Вывод сообщения """
    printLine(message, "\n")
    sys.stdout.flush()

@preloaderStop
def failureMessage(message):
    """ Вывод сообщения """
    printLine(message, "\n")
    sys.stdout.flush()

def separator(symbol="", title=""):
    size = 40
    if title:
        sw = (size - len(title) + 2) / 2
        printLine("%s %s %s" % (symbol*sw, title, symbol*sw))

    else:
        printLine(symbol*size+"\n")

@preloaderStop
def printList(listItems, title="", showSelector=False, showByStep=20):

    if title:
        separator("=", title)

    total = len(listItems)
    printLine("Total found: %d" % total)
    for key, item in enumerate(listItems):
        key += 1

        printLine("%s : %s" % (str(key).rjust(3, " "), item.title if hasattr(item, 'title') else item.name))
        
        if key%showByStep == 0 and key < total:
            printLine("-- More --", "\r")
            tools.getch()
            printLine(" "*12, "\r")
        
    sys.stdout.flush()

    if showSelector:
        printLine("  0 : -Cancel-")
        while True:
            num = raw_input(": ")
            if tools.checkIsInt(num) and  1 <= int(num) <= total:
                return listItems[int(num)-1]
            if num == '0':
                exit(1)
            failureMessage('Incorrect number "%s", please try again:\n' % num)

def printLine(line, endLine="\n"):
    sys.stdout.write(line+endLine)
