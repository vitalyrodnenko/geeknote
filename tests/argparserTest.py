# -*- coding: utf-8 -*-

from geeknote.argparser import *
from cStringIO import StringIO
import sys
import unittest


class testArgparser(unittest.TestCase):

    def setUp(self):
        sys.stdout = StringIO()  # set fake stdout

        # добавляем тестовые данные
        COMMANDS_DICT['testing'] = {
            "help": "Create note",
            "firstArg": "--test_req_arg",
            "arguments": {
                "--test_req_arg": {"altName": "-tra",
                                   "help": "Set note title",
                                   "required": True},
                "--test_arg": {"altName": "-ta",
                               "help": "Add tag to note",
                               "emptyValue": None},
                "--test_arg2": {"altName": "-ta2", "help": "Add tag to note"},
            },
            "flags": {
                "--test_flag": {"altName": "-tf",
                                "help": "Add tag to note",
                                "value": True,
                                "default": False},
            }
        }

    def testEmptyCommand(self):
        parser = argparser([])
        self.assertFalse(parser.parse(), False)

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
        parser = argparser(["testing", "--test_req_arg", "test_req_val",
                            "--test_flag", "--test_arg", "test_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_req_val",
                                          "test_flag": True,
                                          "test_arg": "test_val"})

    def testSuccessCommand2(self):
        parser = argparser(["testing", "test_req_val", "--test_flag",
                            "--test_arg", "test_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_req_val",
                                          "test_flag": True,
                                          "test_arg": "test_val"})

    def testSuccessCommand3(self):
        parser = argparser(["testing", "test_def_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_def_val",
                                          "test_flag": False})

    def testSuccessCommand4(self):
        parser = argparser(["testing", "test_def_val", "--test_arg"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_def_val",
                                          "test_arg": None,
                                          "test_flag": False})

    def testSuccessCommand5(self):
        parser = argparser(["testing", "test_def_val", "--test_arg",
                            "--test_arg2", "test_arg2_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_def_val",
                                          "test_arg": None,
                                          "test_arg2": "test_arg2_val",
                                          "test_flag": False})

    def testSuccessShortAttr(self):
        parser = argparser(["testing", "test_def_val", "-ta",
                            "-ta2", "test_arg2_val"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_def_val",
                                          "test_arg": None,
                                          "test_arg2": "test_arg2_val",
                                          "test_flag": False})

    def testSuccessShortAttr2(self):
        parser = argparser(["testing", "-tra", "test_def_val", "-tf"])
        self.assertEqual(parser.parse(), {"test_req_arg": "test_def_val",
                                          "test_flag": True})
