# -*- coding: utf-8 -*-

# add SqlAlchemy
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SQLALCHEMY = os.path.join(PROJECT_ROOT, 'lib')
sys.path.append( SQLALCHEMY )

import datetime
import pickle

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from log import logging

db_dir_path = os.path.join(os.getenv('USERPROFILE') or os.getenv('HOME'),  '.geeknote')
db_path = os.path.join(db_dir_path, 'database.db')

try:
    if not os.path.exists(db_dir_path):
        os.mkdir(db_dir_path)
except Exception, e:
    logging.error("Can not create dir for database.")

engine = create_engine('sqlite:///' + db_path)
Base = declarative_base()

class Userprop(Base):
    __tablename__ = 'user_props'

    id = Column(Integer, primary_key=True)
    key = Column(String(255))
    value = Column(String(1000))

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return "<Userprop('{0}','{1})>".format(self.key, self.value)
        
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
    guid = Column(String(1000))
    timestamp = Column(DateTime(), nullable = False)

    def __init__(self, guid, name):
        self.guid = guid
        self.name = name
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Notebook('{0}')>".format(self.name)
        
class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    tag = Column(String(255))
    guid = Column(String(1000))
    timestamp = Column(DateTime(), nullable = False)

    def __init__(self, guid, tag):
        self.guid = guid
        self.tag = tag
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Tag('{0}')>".format(self.tag)

class Search(Base):
    __tablename__ = 'search'

    id = Column(Integer, primary_key=True)
    search_obj = Column(Text)
    timestamp = Column(DateTime(), nullable = False)

    def __init__(self, search_obj):
        self.search_obj = search_obj
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Search('{0}')>".format(self.timestamp)
        
#class Search(Base):
#    __tablename__ = 'search'
#
#    id = Column(Integer, primary_key=True)
#    uuid = Column(String(255))
#    name = Column(String(255))
#    stype = Column(String(255))
#    snippet = Column(Text())
#    timestamp = Column(DateTime(), nullable = False)
#
#    def __init__(self, uuid, name, stype, snippet):
#        self.uuid = uuid
#        self.name = name
#        self.stype = stype
#        self.snippet = snippet
#        self.timestamp = datetime.datetime.now()
#
#    def __repr__(self):
#        return "<Search('{0}')>".format(self.name)
        

class Storage(object):
    """
    Class for using database.
    """
    session = None
    
    def __init__(self):
        logging.debug("Storage engine : %s", engine)
        Base.metadata.create_all(engine) 
        Session = sessionmaker(bind=engine)
        self.session = Session()
        
    def logging(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception, e:
                logging.error("%s : %s", func.__name__, str(e))
                return False
        return wrapper
        
    @logging  
    def createUser(self, oAuthToken, info_obj):
        """
        Create user. oAuthToken must be not empty string
        Previous user and user's properties will be removed
        return True if all done
        return False if something wrong
        """
        if not oAuthToken:
            raise Exception("Empty oAuth token")

        if not info_obj:
            raise Exception("Empty user info")
            
        for item in self.session.query(Userprop).all():
            self.session.delete(item)
        
        self.setUserprop('oAuthToken', oAuthToken)
        self.setUserprop('info', pickle.dumps(info_obj))
        
        return True
    
    @logging   
    def getUserToken(self):
        """
        Get user's oAuth token
        return oAuth token if it exists
        return None if there is not oAuth token yet
        return False if something wrong
        """
        return self.getUserprop('oAuthToken')

    @logging   
    def getUserInfo(self):
        """
        Get user's oAuth token
        return oAuth token if it exists
        return None if there is not oAuth token yet
        return False if something wrong
        """
        info = self.getUserprop('info')
        print info
        if info:
            print pickle.loads(info)
            exit(1)
        return None
    
    @logging   
    def getUserprops(self):
        """
        Get all user's properties
        return list of dict if all done
        return [] there are not any user's properties yet
        return False if something wrong
        """
        props = self.session.query(Userprop).all()
        return [{item.key: item.value} for item in props]
    
    @logging   
    def getUserprop(self, key):
        """
        Get user's property by key
        return property's value
        return False if something wrong
        """
        instance = self.session.query(Userprop).filter_by(key=key).first()
        if instance:
            return instance.value
        else:
            return None
    
    @logging   
    def setUserprop(self, key, value):
        """
        Set single user's property. User's property must have key and value
        return True if all done
        return False if something wrong
        """
        instance = self.session.query(Userprop).filter_by(key=key).first()
        if instance:
            instance.value = value
        else:
            instance = Userprop(key, value)
            self.session.add(instance)
        
        self.session.commit()
        return True
    
    @logging   
    def setSettings(self, settings):
        """
        Set multuple settings. Settings must be an instanse dict
        return True if all done
        return False if something wrong
        """
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
    
    @logging   
    def getSettings(self):
        """
        Get all settings
        return list of dict if all done
        return [] there are not any settings yet
        return False if something wrong
        """
        settings = self.session.query(Setting).all()
        result = {}
        for item in settings:
            result[item.key] = item.value
        return result
    
    @logging   
    def setSetting(self, key, value):
        """
        Set single setting. Settings must have key and value
        return True if all done
        return False if something wrong
        """
        instance = self.session.query(Setting).filter_by(key=key).first()
        if instance:
            instance.value = value
        else:
            instance = Setting(key, value)
            self.session.add(instance)
        
        self.session.commit()
        return True
    
    @logging   
    def getSetting(self, key):
        """
        Get setting by key
        return setting's value
        return False if something wrong
        """
        instance = self.session.query(Setting).filter_by(key=key).first()
        if instance:
            return instance.value
        else:
            return None
    
    @logging   
    def setTags(self, tags):
        """
        Set tags. Tags must be an instanse of dict
        Previous tags items will be removed
        return True if all done
        return False if something wrong
        """
        if not isinstance(tags, dict):
            raise Exception("Wrong tags")
            
        for item in self.session.query(Tag).all():
            self.session.delete(item)
        
        for key in tags.keys():
            if not tags[key]:
                raise Exception("Wrong tag's item")
                
            instance = Tag(key, tags[key])
            self.session.add(instance)
        
        self.session.commit()
        return True
    
    @logging   
    def getTags(self):
        """
        Get all tags
        return list of dicts of tags if all done
        return [] there are not any tags yet
        return False if something wrong
        """
        tags = self.session.query(Tag).all()
        result = {}
        for item in tags:
            result[item.guid] = item.tag
        return result
    
    @logging   
    def setNotebooks(self, notebooks):
        """
        Set notebooks. Notebooks must be an instanse of dict
        Previous notebooks items will be removed
        return True if all done
        return False if something wrong
        """
        if not isinstance(notebooks, dict):
            raise Exception("Wrong notebooks")
            
        for item in self.session.query(Notebook).all():
            self.session.delete(item)
        
        for key in notebooks.keys():
            if not notebooks[key]:
                raise Exception("Wrong notebook's item")
                
            instance = Notebook(key, notebooks[key])
            self.session.add(instance)
        
        self.session.commit()
        return True
    
    @logging   
    def getNotebooks(self):
        """
        Get all notebooks
        return list of notebooks if all done
        return [] there are not any notebooks yet
        return False if something wrong
        """
        notebooks = self.session.query(Notebook).all()
        result = {}
        for item in notebooks:
            result[item.guid] = item.name
        return result
        
    @logging
    def setSearch(self, search_obj):
        """
        Set searching.
        Previous searching items will be removed
        return True if all done
        return False if something wrong
        """            
        for item in self.session.query(Search).all():
            self.session.delete(item)
            
        search = pickle.dumps(search_obj)
        instance = Search(search)
        self.session.add(instance)
        
        self.session.commit()
        return True
    
    @logging   
    def getSearch(self):
        """
        Get last searching
        return list of dicts of last searching if all done
        return [] there are not any searching yet
        return False if something wrong
        """
        search = self.session.query(Search).first()
        return pickle.loads(search.search_obj)
    
    #@logging 
    #def setSearch(self, searching):
    #    """
    #    Set searching. Searching must be an instanse of list of dicts
    #    Previous searching items will be removed
    #    return True if all done
    #    return False if something wrong
    #    """
    #    if not isinstance(searching, list):
    #        raise Exception("Wrong searching")
    #        
    #    for item in self.session.query(Search).all():
    #        self.session.delete(item)
    #    
    #    for item in searching:
    #        if not item['uuid'] or not item['name'] or not item['stype'] or not item['snippet']:
    #            raise Exception("Wrong searching item")
    #            
    #        instance = Search(item['uuid'], item['name'], item['stype'], item['snippet'])
    #        self.session.add(instance)
    #    
    #    self.session.commit()
    #    return True
    #
    #@logging   
    #def getSearch(self):
    #    """
    #    Get last searching
    #    return list of dicts of last searching if all done
    #    return [] there are not any searching yet
    #    return False if something wrong
    #    """
    #    searching = self.session.query(Search).all()
    #    return [
    #        {'uuid': item.uuid, 'name': item.name, 'stype': item.stype, 'snippet': item.snippet}
    #        for item in searching]
    