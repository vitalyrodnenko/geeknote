# -*- coding: utf-8 -*-
from argparser import *

import unittest

class testArgparser(unittest.TestCase):

    def setUp(self):
        # добавляем тестовые данные
        COMMANDS_DICT['testing'] = {
            "help": "Create note",
            "firstArg": "--test_req_arg",
            "arguments": {
                "--test_req_arg": {"help": "Set note title", "required": True},
                "--test_arg": {"help": "Add tag to note"},
            },
            "flags": {
                "--test_flag": {"help": "Add tag to note", "value": True, "default": False},
            }
        }

    def testErrorCommands(self):
        parser = argparser(["testing_err", ])
        self.assertFalse(parser.parse(), False)

    def testErrorArg(self):
        parser = argparser(["testing", "test_def_val", "--test_arg_err"])
        self.assertEqual(parser.parse(), False)

    def testErrorNoArg(self):
        parser = argparser(["testing"])
        self.assertEqual(parser.parse(), False)

    def testErrorReq(self):
        parser = argparser(["testing", "--test_arg", "test_val"])
        self.assertEqual(parser.parse(), False)

    def testErrorVal(self):
        parser = argparser(["testing", "--test_req_arg", '--test_arg'])
        self.assertEqual(parser.parse(), False)

    def testErrorFlag(self):
        parser = argparser(["testing", "--test_flag", 'test_val'])
        self.assertEqual(parser.parse(), False)

    def testSuccessCommand1(self):
        parser = argparser(["testing", "--test_req_arg", "test_req_val", "--test_flag", "--test_arg", "test_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_req_val", "test_flag": True, "test_arg": "test_val"})

    def testSuccessCommand2(self):
        parser = argparser(["testing", "test_req_val", "--test_flag", "--test_arg", "test_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_req_val", "test_flag": True, "test_arg": "test_val"})

    def testSuccessCommand3(self):
        parser = argparser(["testing", "test_def_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_def_val", "test_flag": False})

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testArgparser))
    return suite