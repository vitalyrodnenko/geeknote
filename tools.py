# -*- coding: utf-8 -*-

def getch():
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