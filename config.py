# -*- coding: utf-8 -*-

import os, sys

# Evernote config
# !!! DO NOT EDIT !!! >>>
CONSUMER_KEY = "skaizer-1250"
CONSUMER_SECRET = "ed0fcc0c97c032a5"

CONSUMER_KEY_SANDBOX = "skaizer-1250"
CONSUMER_SECRET_SANDBOX = "ed0fcc0c97c032a5"
# !!! DO NOT EDIT !!! <<<

# Application path 
APP_DIR = os.path.join(os.getenv("USERPROFILE") or os.getenv("HOME"),  ".geeknote")

ERROR_LOG = os.path.join(APP_DIR, "error.log")

# Set default system editor
DEF_UNIX_EDITOR = "nano"
DEF_WIN_EDITOR = "notepad.exe"
EDITOR_OPEN = "WRITE"

DEV_MODE = True
DEBUG = False

# validate config
try:
    if not os.path.exists(APP_DIR):
        os.mkdir(APP_DIR)
except Exception, e:
    sys.stdout.write("Can not create application dirictory : %s" % APP_DIR)
    exit()