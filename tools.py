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

class Struct:
    def __init__(self, **entries): 
        self.__dict__.update(entries)