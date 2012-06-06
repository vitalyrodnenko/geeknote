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

        sys.stdout.write(preloader.clearLine)
        if preloader.counter == -1:
            sys.stdout.flush()
            return

        preloader.counter += 1
        sys.stdout.write("%s : %s" % (preloader.progress[preloader.counter % len(preloader.progress)], preloader.message))
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
def SearchResult(result, request):
    """Печать результатов поиска"""
    
    request_row = "Search request: %s \n"
    result_total = "Total found: %d \n"
    result_row = "%(key)s:  %(title)s \n"

    total = len(result)
    sys.stdout.write(request_row % request)
    sys.stdout.write(result_total % total)
    for key, item in result.iteritems():
        sys.stdout.write(result_row % {'key': str(key).rjust(3, " "), 'title': item['title']})
        if key%2 == 0 and key < total:
            sys.stdout.write("-- More -- \r")
            tools.getch()
            sys.stdout.write(" "*10 +"\r")

    sys.stdout.flush()

@preloaderStop
def SelectSearchResult(listItems):
    """Выбор результата поиска"""
    
    total = len(listItems)

    separator("#", "FOUND NOTES")
    sys.stdout.write("Total found: %d \n" % total)

    for key, item in enumerate(listItems):
        sys.stdout.write("%(key)s:  %(title)s \n" % {'key': str(key+1).rjust(3, " "), 'title': item.title})

    sys.stdout.flush()

    while True:
        num = raw_input(": ")
        if tools.checkIsInt(num) and  1 <= int(num) <= total:
            return listItems[int(num)-1]

        failureMessage('Incorrect number "%s", please try again:\n' % num)

@preloaderStop
def removeConfirm(title):
    """Подтверждение удаления заметки"""
    
    sys.stdout.write('Are you sure you want to delete this note: "%s"\n' % title)
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

    separator("#")
    sys.stdout.write("TITLE: %s\n" % note.title)
    separator("=")
    if note.tagNames:
        sys.stdout.write("Tags: %s\n" % ', '.join(note.tagNames))

    sys.stdout.write(editor.ENMLtoText(note.content))
    sys.stdout.flush()

@preloaderStop
def showUser(user, fullInfo):
    def line(key, value):
        if value:
            sys.stdout.write("%s : %s \n" % (key.ljust(16, " "), value))

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
    sys.stdout.write(message+"\n")
    sys.stdout.flush()

@preloaderStop
def failureMessage(message):
    """ Вывод сообщения """
    sys.stdout.write(message+"\n")
    sys.stdout.flush()

def separator(symbol="", title=""):

    size = 40
    if title:
        sw = (size - len(title) + 2) / 2
        sys.stdout.write("%s %s %s \n" % (symbol*sw, title, symbol*sw))

    else:
        sys.stdout.write(symbol*size+"\n")