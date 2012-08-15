# -*- coding: utf-8 -*-

import out
import sys
import time


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
        import sys
        import tty
        import termios
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
        items = data.iteritems()
        return dict([[key.strip(' \t\n\r\"\''), val] for key, val in items])

    if isinstance(data, list):
        return map(lambda val: val.strip(' \t\n\r\"\''), data)

    if isinstance(data, str):
        return data.strip(' \t\n\r\"\'')

    raise Exception("Unexpected args type: "
                    "%s. Expect list or dict" % type(data))


class ExitException(Exception):
    pass


def exit(message='exit'):
    out.preloader.exit()
    time.sleep(0.33)
    raise ExitException(message)


def KeyboardInterruptSignalHendler(signal, frame):
    exit()


class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)


def decodeArgs(args):
    return map(lambda val: stdinEncode(val), args)


def stdoutEncode(data):
    try:
        return data.decode("utf8").encode(sys.stdout.encoding)
    except:
        return data


def stdinEncode(data):
    try:
        return data.decode(sys.stdin.encoding).encode("utf8")
    except:
        return data
