# -*- coding: utf-8 -*-

import os
import sys

# !!! DO NOT EDIT !!! >>>
USER_BASE_URL = "www.evernote.com"
USER_STORE_URI = "https://www.evernote.com/edam/user"
CONSUMER_KEY = "skaizer-5314"
CONSUMER_SECRET = "6f4f9183b3120801"

USER_BASE_URL_SANDBOX = "sandbox.evernote.com"
USER_STORE_URI_SANDBOX = "https://sandbox.evernote.com/edam/user"
CONSUMER_KEY_SANDBOX = "skaizer-1250"
CONSUMER_SECRET_SANDBOX = "ed0fcc0c97c032a5"
# !!! DO NOT EDIT !!! <<<

# Evernote config

VERSION = 0.1

IS_IN_TERMINAL = sys.stdin.isatty()
IS_OUT_TERMINAL = sys.stdout.isatty()

# Application path
APP_DIR = os.path.join(os.getenv("HOME") or os.getenv("USERPROFILE"),  ".geeknote")
ERROR_LOG = os.path.join(APP_DIR, "error.log")

# Set default system editor
DEF_UNIX_EDITOR = "nano"
DEF_WIN_EDITOR = "notepad.exe"
EDITOR_OPEN = "WRITE"

REMINDER_NONE = "NONE"
REMINDER_DONE = "DONE"
REMINDER_DELETE = "DELETE"
# Shortcuts have a word and a number of seconds to add to the current time
REMINDER_SHORTCUTS = {'TOMORROW': 86400000, 'WEEK': 604800000}

DEV_MODE = False
DEBUG = False

# Url view the note
NOTE_URL = "https://%domain%/Home.action?#n=%s"

# validate config
try:
    if not os.path.exists(APP_DIR):
        os.mkdir(APP_DIR)
except Exception, e:
    sys.stdout.write("Can not create application dirictory : %s" % APP_DIR)
    exit()

if DEV_MODE:
    USER_STORE_URI = USER_STORE_URI_SANDBOX
    CONSUMER_KEY = CONSUMER_KEY_SANDBOX
    CONSUMER_SECRET = CONSUMER_SECRET_SANDBOX
    USER_BASE_URL = USER_BASE_URL_SANDBOX

NOTE_URL = NOTE_URL.replace('%domain%', USER_BASE_URL)
