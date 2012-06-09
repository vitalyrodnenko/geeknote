# -*- coding: utf-8 -*-

import os, sys
import glob

from geeknote import GeekNote

if __name__ == "__main__":
    
    gn = GeekNote()
    #r = gn.createNote(title="note title", content="content")
    r = gn.findNotes(keywords="note", count=1)
    print(r)
    
    #path = "/home/ivan/WebDevelop/geeknote/sync_dir_example/"
    #mask = '*'
    
    #files = glob.iglob("{0}{1}".format(path, mask))
    #
    #for f in files:
    #    if os.path.isfile(f):
    #        print(os.path.getmtime(f))