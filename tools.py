# -*- coding: utf-8 -*-
from log import logging
import sys

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

def exit():
    sys.exit(1)

def confirm(prompt_str="Confirm", allow_empty=False, default=False):
    """
    Allows to ask user action from console. It asks a question and gives ability to answer Y or N.
    """
    fmt = (prompt_str, 'y', 'n') if default else (prompt_str, 'n', 'y')
    if allow_empty:
        prompt = '%s [%s]|%s: ' % fmt
    else:
        prompt = '%s %s|%s: ' % fmt
    while True:
        ans = raw_input(prompt).lower()
        if ans == '' and allow_empty:
            return default
        elif ans == 'y':
            return True
        elif ans == 'n':
            return False
        else:
            print 'Please enter y or n.'

class Struct:
    def __init__(self, **entries): 
        self.__dict__.update(entries)