# -*- coding: utf-8 -*-

import os, sys
import glob

from geeknote import GeekNote, Notebooks, Notes
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
        #set path
        if not path:
            raise Exception("Path to sync directories does not select.")
        
        if not os.path.exists(path):
            raise Exception("Path to sync directories does not exist.")
        
        if path[-1] != '/':
            path = path + '/'
        
        self.path = path
            
        #set mask
        if not self.mask:
            self.mask = "*.*"
         
        #set notebook
        self.notebook_guid, self.notebook_name = self._get_notebook(notebook_name)
    
    @log
    def sync(self):
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
        if notebook_name:
            guid = Notebooks().getNoteGUID(notebook_name)
            
            if not guid:
                guid = GeekNote().createNotebook(notebook_name).guid
                
            return (guid, notebook_name)
        else:
            nb_list = GeekNote().findNotebooks()
            
            for nb in nb_list:
                if nb.defaultNotebook:
                    return (nb.guid, nb.name)
    
    @log                
    def _get_files(self):
        """
        Get files by self.mask from self.path dir.
        """ 
        file_paths = glob.iglob("{0}{1}".format(self.path, self.mask))
        
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
        keywords = 'notebook:{0}'.format(tools.strip(self.notebook_name))
        return GeekNote().findNotes(keywords, 10000).notes
            

if __name__ == "__main__":
    
    notebook_name = ''
    path = "/home/www-dev/varche1/geeknote/sync_dir_example/"
    mask = '*.*'
    
    GNS = GNSync(notebook_name, path, mask)
    GNS.sync()