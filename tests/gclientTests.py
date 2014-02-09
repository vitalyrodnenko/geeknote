# -*- coding: utf-8 -*-

import unittest

from geeknote.gclient import CustomClient
from geeknote.geeknote import UserStore


class testGclient(unittest.TestCase):

    def test_patched_client(self):
        self.assertEquals(UserStore.Client, CustomClient)

    def test_patched_client_contain_methods(self):
        METHODS = dir(UserStore.Client)
        self.assertIn('getNoteStoreUrl', METHODS)
        self.assertIn('send_getNoteStoreUrl', METHODS)
        self.assertIn('recv_getNoteStoreUrl', METHODS)
