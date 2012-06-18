# -*- coding: utf-8 -*-
from argparser import *

import unittest

class testArgparser(unittest.TestCase):

    def setUp(self):
        # добавляем тестовые данные
        COMMANDS_DICT['testing'] = {
            "help": "Create note",
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
        self.assertEqual(parser.parse(), ['error-cmd', 'testing_err'])

    def testErrorArg(self):
        parser = argparser(["testing", "--test_arg_err"])
        self.assertEqual(parser.parse(), ['error-arg', 'testing', '--test_arg_err'])

    def testErrorReq(self):
        parser = argparser(["testing", "--test_arg", "test_val"])
        self.assertEqual(parser.parse(), ['error-req', 'testing', '--test_req_arg'])

    def testErrorVal(self):
        parser = argparser(["testing", "--test_req_arg", '--test_arg'])
        self.assertEqual(parser.parse(), ['error-val', '--test_req_arg', '--test_arg'])

    def testErrorFlag(self):
        parser = argparser(["testing", "--test_flag", 'test_val'])
        self.assertEqual(parser.parse(), ['error-arg', 'testing', 'test_val'])

    def testSuccessCommand(self):
        parser = argparser(["testing", "--test_req_arg", "test_req_val", "--test_flag", "--test_arg", "test_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_req_val", "test_flag": True, "test_arg": "test_val"})

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testArgparser))
    return suite