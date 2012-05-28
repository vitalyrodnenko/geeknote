# -*- coding: utf-8 -*-

import datetime

from sqlalchemy import *
from sqlalchemy.orm import *

engine = create_engine('sqlite:///geeknote.db', echo=True)

class User(object):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    token = Column(String(255))
    login = Column(String(255))

    def __init__(self, token, login):
        self.token = token
        self.login = login

    def __repr__(self):
        return "<User('{0}','{1})>".format(self.login, self.token)
        
class Setting(object):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    key = Column(String(255))
    value = Column(String(1000))
    user_id = Column(Integer, ForeignKey('users.id'))
    
    user = relationship("User", backref=backref('settings', order_by=id))

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return "<Setting('{0}','{1})>".format(self.key, self.value)
        
class Notebook(object):
    __tablename__ = 'notebooks'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    user_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime(), nullable = False)
    
    user = relationship("User", backref=backref('notebooks', order_by=id))

    def __init__(self, name):
        self.name = name
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Notebook('{0}')>".format(self.name)
        
notes_tags = Table('notes_tags', MetaData(),
    Column('note_id', Integer, ForeignKey('notes.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)
        
class Note(object):
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    content = Column(Text())
    notebook_id = Column(Integer, ForeignKey('notebooks.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime(), nullable = False)
    
    tags = relationship('Tag', secondary=notes_tags, backref='notes')
    user = relationship("User", backref=backref('notes', order_by=id))
    notebook = relationship("Notebook", backref=backref('notes', order_by=id))

    def __init__(self, title, content):
        self.title = title
        self.content = content
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Note('{0}')>".format(self.title)
        
class Tag(object):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    tag = Column(String(255))
    user_id = Column(Integer, ForeignKey('users.id'))
    parent_id = Column(Integer, ForeignKey('tags.id'))
    timestamp = Column(DateTime(), nullable = False)
    
    user = relationship("User", backref=backref('tags', order_by=id))
    parent = relationship("Tag", backref=backref('tags', order_by=id))

    def __init__(self, tag):
        self.title = tag
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "<Tag('{0}')>".format(self.tag)

