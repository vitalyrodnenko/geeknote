# -*- coding: utf-8 -*-

import datetime

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from log import logging

engine = create_engine('sqlite:///geeknote1.db', echo=True)
Base = declarative_base()

class User(Base):
    __tablename__ = 'user_info'

    id = Column(Integer, primary_key=True)
    token = Column(String(255))
    login = Column(String(255))

    def __init__(self, token, login):
        self.token = token
        self.login = login

    def __repr__(self):
        return "<User('{0}','{1})>".format(self.login, self.token)
        
class Setting(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    key = Column(String(255))
    value = Column(String(1000))
    
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return "<Setting('{0}','{1})>".format(self.key, self.value)
        
class Notebook(Base):
    __tablename__ = 'notebooks'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    #uuid = Column(String(255))
    #parent_id = Column(Integer, ForeignKey('notebooks.id'))
    timestamp = Column(DateTime(), nullable = False)
    
    #parent = relationship("Notebook", backref=backref('notebooks', order_by=id))

    def __init__(self, name):
        self.name = name
        #self.uuid = uuid
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Notebook('{0}')>".format(self.name)
        
class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    tag = Column(String(255))
    #parent_id = Column(Integer, ForeignKey('tags.id'))
    timestamp = Column(DateTime(), nullable = False)
    
    #parent = relationship("Tag", backref=backref('tags', order_by=id))

    def __init__(self, tag):
        self.tag = tag
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Tag('{0}')>".format(self.tag)
        
class Search(Base):
    __tablename__ = 'search'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(255))
    name = Column(String(255))
    stype = Column(String(255))
    snippet = Column(Text())
    timestamp = Column(DateTime(), nullable = False)

    def __init__(self, uuid, name, stype, snippet):
        self.uuid = uuid
        self.name = name
        self.stype = stype
        self.snippet = snippet
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Search('{0}')>".format(self.name)
        

class Storage(object):
    """
    Class for using database.
    """
    session = None
    
    def __init__(self):
        Base.metadata.create_all(engine) 
        Session = sessionmaker(bind=engine)
        self.session = Session()
        
    def setSettings(self, settings):
        """
        Set multuple settings. Settings must be an instanse dict
        return True if all done
        return False if something wrong
        """
        try:
            if not isinstance(settings, dict):
                raise Exception("Wrong settings")
            
            for key in settings.keys():
                if not settings[key]:
                    raise Exception("Wrong setting's item")
                    
                instance = self.session.query(Setting).filter_by(key=key).first()
                if instance:
                    instance.value = settings[key]
                else:
                    instance = Setting(key, settings[key])
                    self.session.add(instance)
            
            self.session.commit()
            return True
        except Exception, e:
            logging.error("Settings setter: %s:/%s. Error: %s", key, value, str(e))
            return False
        
    def getSettings(self):
        """
        Get all settings
        return list of dict if all done
        return [] there are not any settings yet
        return False if something wrong
        """
        try:
            settings = self.session.query(Setting).all()
            return [{item.key: item.value} for item in settings]
        except Exception, e:
            logging.error("Settings getter. Error: %s", str(e))
            return False
        
    def setSetting(self, key, value):
        """
        Set single setting. Settings must have key and value
        return True if all done
        return False if something wrong
        """
        try:
            instance = self.session.query(Setting).filter_by(key=key).first()
            if instance:
                instance.value = value
            else:
                instance = Setting(key, value)
                self.session.add(instance)
            
            self.session.commit()
            return True
        except Exception, e:
            logging.error("Setting setter: %s:/%s. Error: %s", key, value, str(e))
            return False
        
    def getSetting(self, key):
        """
        Get setting by key
        return setting's value
        return False if something wrong
        """
        try:
            instance = self.session.query(Setting).filter_by(key=key).first()
            if instance:
                return instance.value
            else:
                return None
        except Exception, e:
            logging.error("Setting geter: %s. Error: %s", key, str(e))
            return False
        
    def setTags(self, tags):
        """
        Set tags. Tags must be an instanse of list
        Previous tags items will be removed
        return True if all done
        return False if something wrong
        """
        try:
            if not isinstance(tags, list):
                raise Exception("Wrong tags")
                
            for item in self.session.query(Tag).all():
                self.session.delete(item)
            
            for tag in tags:
                if not tag:
                    raise Exception("Empty tag")
                    
                instance = Tag(tag)
                self.session.add(instance)
            
            self.session.commit()
            return True
        except Exception, e:
            logging.error("Tags setter: %s. Error: %s", tags, str(e))
            return False
        
    def getTags(self):
        """
        Get all tags
        return list of tags if all done
        return [] there are not any tags yet
        return False if something wrong
        """
        try:
            tags = self.session.query(Tag).all()
            return [item.tag for item in tags]
        except Exception, e:
            logging.error("Tags getter. Error: %s", str(e))
            return False
        
    def setNotebooks(self, notebooks):
        """
        Set notebooks. Notebooks must be an instanse of list
        Previous notebooks items will be removed
        return True if all done
        return False if something wrong
        """
        try:
            if not isinstance(notebooks, list):
                raise Exception("Wrong notebooks")
                
            for item in self.session.query(Notebook).all():
                self.session.delete(item)
            
            for notebook in notebooks:
                if not notebook:
                    raise Exception("Empty notebook")
                    
                instance = Notebook(notebook)
                self.session.add(instance)
            
            self.session.commit()
            return True
        except Exception, e:
            logging.error("Notebooks setter: %s. Error: %s", notebooks, str(e))
            return False
        
    def getNotebooks(self):
        """
        Get all notebooks
        return list of notebooks if all done
        return [] there are not any notebooks yet
        return False if something wrong
        """
        try:
            notebooks = self.session.query(Notebook).all()
            return [item.name for item in notebooks]
        except Exception, e:
            logging.error("Notebooks getter. Error: %s", str(e))
            return False

    def setSearch(self, searching):
        """
        Set searching. Searching must be an instanse of list of dicts
        Previous searching items will be removed
        return True if all done
        return False if something wrong
        """
        try:
            if not isinstance(searching, list):
                raise Exception("Wrong searching")
                
            for item in self.session.query(Search).all():
                self.session.delete(item)
            
            for item in searching:
                if not item['uuid'] or not item['name'] or not item['stype'] or not item['snippet']:
                    raise Exception("Wrong searching item")
                    
                instance = Search(item['uuid'], item['name'], item['stype'], item['snippet'])
                self.session.add(instance)
            
            self.session.commit()
            return True
        except Exception, e:
            logging.error("Search setter. Error: %s", str(e))
            return False
        
    def getSearch(self):
        """
        Get last searching
        return list of dicts of last searching if all done
        return [] there are not any searching yet
        return False if something wrong
        """
        try:
            searching = self.session.query(Search).all()
            return [
                {'uuid': item.uuid, 'name': item.name, 'stype': item.stype, 'snippet': item.snippet}
                for item in searching]
        except Exception, e:
            logging.error("Search getter. Error: %s", str(e))
            return False
    
