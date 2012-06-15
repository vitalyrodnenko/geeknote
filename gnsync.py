# -*- coding: utf-8 -*-

import argparse
import os, sys
import glob
import logging

from geeknote import GeekNote
from storage import Storage
import editor
import tools

# set default logger (write log to file)
def_logpath = "{0}/GeekNoteSync.log".format(os.getenv('USERPROFILE') or os.getenv('HOME'))
formatter = logging.Formatter('%(asctime)-15s : %(message)s')
handler = logging.FileHandler(def_logpath)
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

def log(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            logger.error("%s", str(e))
    return wrapper

@log
def reset_logpath(logpath):
    """
    Reset logpath to path from command line
    """
    global logger
    
    if not logpath:
        return
    
    # remove temporary log file if it's empty
    if os.path.isfile(def_logpath):
        if os.path.getsize(def_logpath) == 0:
            os.remove(def_logpath)
    
    # save previous handlers    
    handlers = logger.handlers
    
    # remove old handlers
    for handler in handlers:
        logger.removeHandler(handler)
        
    # try to set new file handler
    handler = logging.FileHandler(logpath)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class GNSync:
    
    notebook_name = None
    path = None
    mask = None
    
    notebook_guid = None
    all_set = False
    
    @log
    def __init__(self, notebook_name, path, mask):
        # check auth
        if not Storage().getUserToken():
            raise Exception("Auth error. There is not any oAuthToken.")
            
        #set path
        if not path:
            raise Exception("Path to sync directories does not select.")
        
        if not os.path.exists(path):
            raise Exception("Path to sync directories does not exist.")
        
        if path[-1] != '/':
            path = path + '/'
        
        self.path = path
            
        #set mask
        if not mask:
            mask = "*.*"
            
        self.mask = mask
        
        logger.info('Sync Start')
         
        #set notebook
        self.notebook_guid, self.notebook_name = self._get_notebook(notebook_name)
        
        # all is Ok
        self.all_set = True
    
    @log
    def sync(self):
        """
        Synchronize files to notes 
        """
        if not self.all_set:
            return
        
        files =  self._get_files()
        notes = self._get_notes()

        for f in files:
            has_note = False
            for n in notes:
                if f['name'] == n.title:
                    has_note = True
                    if f['mtime'] > n.updated:
                        self._update_note(f, n)
                        break
                    
            if not has_note :
                self._create_note(f)
                
        logger.info('Sync Complite')
    
    @log
    def _update_note(self, file_note, note):
        """
        Updates note from file
        """
        body = open(file_note['path'], "r").read()
        body = editor.textToENML(body)
        
        result = GeekNote().updateNote(
            guid=note.guid,
            title=note.title,
            content=body,
            notebook=self.notebook_guid)
        
        if result:
            logger.info('Note "{0}" was updated'.format(note.title))
        else:
            raise Exception('Note "{0}" was not updated'.format(note.title))
            
        return result
        
    
    @log  
    def _create_note(self, file_note):
        """
        Creates note from file
        """
        body = open(file_note['path'], "r").read()
        body = editor.textToENML(body)
        
        result = GeekNote().createNote(
            title=file_note['name'],
            content=body,
            notebook=self.notebook_guid)
        
        if result:
            logger.info('Note "{0}" was created'.format(file_note['name']))
        else:
            raise Exception('Note "{0}" was not created'.format(file_note['name']))
            
        return result
    
    @log  
    def _get_notebook(self, notebook_name):
        """
        Get notebook guid and name. Takes default notebook if notebook's name does not
        select.
        """
        notebooks = GeekNote().findNotebooks()
        
        if notebook_name:
            notebook = [item for item in notebooks if item.name == notebook_name]
            guid = None
            if notebook:
                guid = notebook[0].guid
            
            if not guid:
                notebook = GeekNote().createNotebook(notebook_name)
                
                if(notebook):
                    logger.info('Notebook "{0}" was created'.format(notebook_name))
                else:
                    raise Exception('Notebook "{0}" was not created'.format(notebook_name))
                    
                guid = notebook.guid
                
            return (guid, notebook_name)
        else:
            for nb in notebooks:
                if nb.defaultNotebook:
                    return (nb.guid, nb.name)
    
    @log             
    def _get_files(self):
        """
        Get files by self.mask from self.path dir.
        """ 
        file_paths = glob.glob("{0}{1}".format(self.path, self.mask))
        
        files = []
        for f in file_paths:
            if os.path.isfile(f):
                file_name = os.path.basename(f)
                file_name = os.path.splitext(file_name)[0]
                
                mtime = int(os.path.getmtime(f) * 1000)
                
                files.append({'path': f,'name': file_name, 'mtime': mtime})
        
        return files
    
    @log 
    def _get_notes(self):
        """
        Get notes from evernote.
        """        
        keywords = 'notebook:"{0}"'.format(tools.strip(self.notebook_name))
        return GeekNote().findNotes(keywords, 10000).notes
            

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--path', '-p', action='store', help='Path to synchronize directory')
        parser.add_argument('--mask', '-m', action='store', help='Mask of files to synchronize. Default is "*.*"')
        parser.add_argument('--notebook', '-n', action='store', help='Notebook name for synchronize. Default is default notebook')
        parser.add_argument('--logpath', '-l', action='store', help='Path to log file. Default is GeekNoteSync in home dir')
        
        args = parser.parse_args()
    
        path = args.path if args.path else None
        mask = args.mask if args.mask else None
        notebook = args.notebook if args.notebook else None
        logpath = args.logpath if args.logpath else None
        
        reset_logpath(logpath)
        
        GNS = GNSync(notebook, path, mask)
        GNS.sync()
        
    except Exception, e:
        logger.error(str(e));