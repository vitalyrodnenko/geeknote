# -*- coding: utf-8 -*-

import os

# Evernote config
# !!! DO NOT EDIT !!!
CONSUMER_KEY = "skaizer-1250"
CONSUMER_SECRET = "ed0fcc0c97c032a5"

# Application path 
APP_DIR = os.path.join(os.getenv("USERPROFILE") or os.getenv("HOME"),  ".geeknote")

ERROR_LOG = os.path.join(APP_DIR, "error.log")

# Set default system editor
DEF_UNIX_EDITOR = "nano"
DEF_WIN_EDITOR = "notepad.exe"
EDITOR_OPEN_PARAM = "WRITE"

DEV_MODE = True
DEBUG = False