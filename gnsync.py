# -*- coding: utf-8 -*-

import argparse
import os, sys
import glob

from geeknote import GeekNote
from storage import Storage
from log import logging, log
import editor
import tools

class GNSync:
    
    notebook_name = None
    path = None
    mask = None
    
    notebook_guid = None
    
    @log
    def __init__(self, notebook_name, path, mask):
        #set log file
        #if not log_path:
        #    log_path = "{0}/GeekNoteSync.log".format(os.getenv('USERPROFILE') or os.getenv('HOME'))
        
        #logging.basicConfig(filename=log_path)
        
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
         
        #set notebook
        self.notebook_guid, self.notebook_name = self._get_notebook(notebook_name)
    
    @log
    def sync(self):
        """
        Synchronize files to notes 
        """
        files =  self._get_files()
        notes = self._get_notes()
        
        #print(files)
        #print(notes)
        #print(self.notebook_name)
        #print(self.notebook_guid)

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
                
        log.info('Sync Complite')
    
    @log
    def _update_note(self, file_note, note):
        """
        Updates note from file
        """
        body = open(file_note['path'], "r").read()
        body = editor.textToENML(body)
        
        return GeekNote().updateNote(
            guid=note.guid,
            title=note.title,
            content=body,
            notebook=self.notebook_guid)         
    
    @log    
    def _create_note(self, file_note):
        """
        Creates note from file
        """
        body = open(file_note['path'], "r").read()
        body = editor.textToENML(body)
        
        return GeekNote().createNote(
            title=file_note['name'],
            content=body,
            notebook=self.notebook_guid)    
    
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
                guid = GeekNote().createNotebook(notebook_name).guid
                
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
        #parser.add_argument('--log', '-l', action='store', help='Path to log file. Default is GeekNoteSync in home dir')
        
        args = parser.parse_args()
    
        path = args.path if args.path else None
        mask = args.mask if args.mask else None
        notebook = args.notebook if args.notebook else None
        #log_path = args.log_path if args.log_path else None
        
        #GNS = GNSync('t2', '/home/www-dev/varche1/geeknote/sync_dir_example', '*.*', '/home/www-dev/varche1/geeknote/LOG.log')
        
        GNS = GNSync(notebook, path, mask)
        GNS.sync()
        
    except Exception, e:
        pass