# -*- coding: utf-8 -*-
import getpass
import time
import sys
import thread
from tools import getch
from i18n import LNG


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
def SearchResult(result):
    """Печать результатов поиска"""
    
    request_row = "%(request_title)s : %(request)s \n"
    result_total = "%(find_total)s : %(total)d \n"
    result_row = "%(key)s:  %(title)s \n"

    total = len(result)
    sys.stdout.write(result_total % {'find_total': LNG['find_total'], 'total': total })
    for key, item in result.iteritems():
        sys.stdout.write(result_row % {'key': str(key).rjust(3, " "), 'title': item['title']})
        if key%2 == 0 and key < total:
            sys.stdout.write("-- More -- \r")
            getch()
            sys.stdout.write(" "*10 +"\r")

    sys.stdout.flush()