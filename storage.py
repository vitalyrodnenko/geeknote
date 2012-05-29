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
    uuid = Column(String(255))
    #parent_id = Column(Integer, ForeignKey('notebooks.id'))
    timestamp = Column(DateTime(), nullable = False)
    
    #parent = relationship("Notebook", backref=backref('notebooks', order_by=id))

    def __init__(self, name, uuid):
        self.name = name
        self.uuid = uuid
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
        self.title = tag
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Tag('{0}')>".format(self.tag)

class Storage(object):
    session = None
    
    def __init__(self):
        Base.metadata.create_all(engine) 
        Session = sessionmaker(bind=engine)
        self.session = Session()
        
    def setSettings(self, settings):
        try:
            if not isinstance(settings, list):
                raise Exception("Wrong settings")
            for item in settings:
                if not item['key'] or not item['value']:
                    raise Exception("Wrong setting's item")
                    
                instance = self.session.query(Setting).filter_by(key=item['key']).first()
                if instance:
                    instance.value = item['value']
                else:
                    instance = Setting(item['key'], item['value'])
                    self.session.add(instance)
            
            self.session.commit()
            return True
        except Exception, e:
            logging.error("Settings setter: %s:/%s", key, value)
            return False
        
    def getSettings(self):
        try:
            return self.session.query(Setting).all()
        except Exception, e:
            logging.error("Settings getter")
            return False
        
    def setSetting(self, key, value):
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
            logging.error("Setting setter: %s:/%s", key, value)
            return False
        
    def getSetting(self, key):
        try:
            instance = self.session.query(Setting).filter_by(key=key).first()
            if instance:
                return instance.value
            else:
                return None
        except Exception, e:
            logging.error("Setting geter: %s", key)
            return False

    
