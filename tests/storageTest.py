# -*- coding: utf-8 -*-

import unittest
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker
from geeknote import storage
import pickle


def hacked_init(self):
    '''Hack for testing'''
    engine = create_engine('sqlite:///:memory:', echo=False)
    storage.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    self.session = Session()


class storageTest(unittest.TestCase):
    def setUp(self):
        stor = storage.Storage
        stor.__init__ = hacked_init
        self.storage = stor()
        self.otoken = 'testoauthtoken'
        self.userinfo = {'email': 'test@mail.com'}
        self.tags = {u'tag': 1, u'tag2': 2, u'tag3': 'lol'}
        self.notebooks = {u'notebook': u'mylaptop'}
        self.storage.createUser(self.otoken,
                                self.userinfo)

    def test_create_user_without_token_fail(self):
        self.assertFalse(self.storage.createUser(None, self.userinfo))

    def test_create_user_without_info_fail(self):
        self.assertFalse(self.storage.createUser(self.otoken, None))

    def test_remove_user_success(self):
        self.assertTrue(self.storage.removeUser())

    def test_get_user_token_success(self):
        self.assertEquals(self.storage.getUserToken(), self.otoken)

    def test_get_user_info_success(self):
        self.assertEquals(self.storage.getUserInfo(), self.userinfo)

    def test_get_user_props_success(self):
        props = [{u'oAuthToken': 'testoauthtoken'},
                 {u'info': {'email': 'test@mail.com'}}]
        self.assertEquals(self.storage.getUserprops(), props)

    def test_get_user_props_exists_success(self):
        self.assertEquals(self.storage.getUserprop('info'),
                             self.userinfo)

    def test_get_user_prop_not_exists(self):
        self.assertFalse(self.storage.getUserprop('some_prop'))

    def test_set_new_user_prop(self):
        self.assertFalse(self.storage.getUserprop('kkey'))
        self.assertTrue(self.storage.setUserprop('some_key', 'some_value'))
        self.assertEquals(self.storage.getUserprop('some_key'), 'some_value')

    def test_set_exists_user_prop(self):
        newmail = {'email': 'new_email@mail.com'}
        self.assertEquals(self.storage.getUserprop('info'), self.userinfo)
        self.assertTrue(self.storage.setUserprop('info', newmail), newmail)
        self.assertEquals(self.storage.getUserprop('info'), newmail)

    def test_get_empty_settings(self):
        self.assertEquals(self.storage.getSettings(), {})

    def test_set_settings_success(self):
        self.storage.setSettings({'editor': 'vim'})
        self.assertEquals(self.storage.getSettings(),
                             {u'editor': u"S'vim'\np0\n."})

    def test_set_setting_error_type_fail(self):
        self.assertFalse(self.storage.setSettings('editor'))

    def test_set_setting_none_value_fail(self):
        self.assertFalse(self.storage.setSettings({'key': None}))

    def test_update_settings_fail(self):
        self.storage.setSettings({'editor': 'vim'})
        self.assertTrue(self.storage.setSettings({'editor': 'nano'}))
        self.assertEquals(self.storage.getSettings(),
                             {u'editor': u"S'nano'\np0\n."})

    def test_get_setting_exist_success(self):
        self.storage.setSettings({'editor': 'vim'})
        editor = self.storage.getSetting('editor')
        self.assertEquals(pickle.loads(editor), 'vim')

    def test_set_setting_true(self):
        editor = 'nano'
        self.assertTrue(self.storage.setSetting('editor', editor))
        self.assertEquals(self.storage.getSetting('editor'), editor)

    def test_get_setting_not_exist_fail(self):
        self.assertFalse(self.storage.getSetting('editor'))

    def test_set_tags_success(self):
        self.assertTrue(self.storage.setTags(self.tags))

    def test_set_tags_error_type_fail(self):
        self.assertFalse(self.storage.setTags('tag'))

    def test_set_tags_none_value_fail(self):
        self.assertFalse(self.storage.setTags({'tag': None}))

    def test_get_tags_success(self):
        tags = {u'tag': u'1', u'tag2': u'2', u'tag3': u'lol'}
        self.assertTrue(self.storage.setTags(self.tags))
        self.assertEquals(self.storage.getTags(), tags)

    def test_replace_tags_success(self):
        tags = {u'tag': u'1', u'tag2': u'2', u'tag3': u'3'}
        self.assertTrue(self.storage.setTags(self.tags))
        self.tags[u'tag3'] = 3
        self.assertTrue(self.storage.setTags(self.tags))
        self.assertEquals(self.storage.getTags(), tags)

    def test_set_notebooks_success(self):
        self.assertEquals(self.storage.getNotebooks(), {})
        self.storage.setNotebooks(self.notebooks)
        self.assertEquals(self.storage.getNotebooks(), self.notebooks)

    def test_replace_notebooks_success(self):
        newnotebooks = {u'notebook': u'android'}
        self.storage.setNotebooks(self.notebooks)
        self.storage.setNotebooks(newnotebooks)
        self.assertEquals(self.storage.getNotebooks(), newnotebooks)

    def test_get_empty_search_success(self):
        self.assertFalse(self.storage.getSearch())

    def test_get_search_exists_success(self):
        query = 'my query'
        self.assertTrue(self.storage.setSearch(query))
        self.assertEquals(self.storage.getSearch(), query)

    def test_set_notebooks_error_type_fail(self):
        self.assertFalse(self.storage.setNotebooks('book'))

    def test_set_notebooks_none_value_fail(self):
        self.assertFalse(self.storage.setNotebooks({'book': None}))

    def test_set_search_true(self):
        self.assertTrue(self.storage.setSearch('my query'))


class modelsTest(unittest.TestCase):
    def test_rept_userprop(self):
        userprop = storage.Userprop(key='test',
                                    value='value')
        self.assertEquals(userprop.__repr__(),
                         "<Userprop('test','value)>")

    def test_repr_setting(self):
        setting = storage.Setting(key='test',
                                  value='value')
        self.assertEquals(setting.__repr__(),
                         "<Setting('test','value)>")

    def test_repr_notebook(self):
        notebook = storage.Notebook(name='notebook',
                                    guid='testguid')
        self.assertEquals(notebook.__repr__(),
                         "<Notebook('notebook')>")

    def test_repr_tag(self):
        tag = storage.Tag(tag='testtag',
                          guid='testguid')
        self.assertEquals(tag.__repr__(), "<Tag('testtag')>")

    def test_repr_search(self):
        search = storage.Search(search_obj='query')
        self.assertEquals(search.__repr__(),
                         "<Search('%s')>" % search.timestamp)
