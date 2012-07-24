#!/usr/bin/env python

import sys
import unittest
from cStringIO import StringIO
from geeknote.config import VERSION
from geeknote.out import printDate, printLine, printAbout,\
    separator, failureMessage, successMessage, showUser, showNote, \
    printList, SearchResult
from geeknote import out


class AccountingStub(object):
    uploadLimit = 100
    uploadLimitEnd = 100000


class UserStub(object):
    username = 'testusername'
    name = 'testname'
    email = 'testemail'
    accounting = AccountingStub()


class NoteStub(object):
    title = 'testnote'
    created = 10000
    updated = 100000
    content = '##note content'
    tagNames = ['tag1', 'tag2', 'tag3']
    guid = 12345


class outTestsWithHackedStdout(unittest.TestCase):

    def setUp(self):
        sys.stdout = StringIO()  # set fake stdout

    def test_print_line(self):
        printLine('test')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), 'test\n')

    def test_print_line_other_endline_success(self):
        printLine('test', endLine='\n\r')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), 'test\n\r')

    def test_print_about_success(self):
        about = '''Version: %s
Geeknote - a command line client for Evernote.
Use geeknote --help to read documentation.
And visit www.geeknote.me to check for updates.\n''' % VERSION
        printAbout()
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), about)

    def test_separator_with_title_success(self):
        line = '------------------- test ------------------\n'
        separator(symbol='-', title='test')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), line)

    def test_separator_without_title_success(self):
        line = '----------------------------------------\n\n'
        separator(symbol='-')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), line)

    def test_separator_empty_args_success(self):
        separator()
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), '\n\n')

    def test_failure_message_success(self):
        failureMessage('fail')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), 'fail\n')

    def test_success_message_success(self):
        successMessage('success')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), 'success\n')

    def test_show_user_without_fullinfo_success(self):
        showUser(UserStub(), {})
        info = '''################ USER INFO ################
Username         : testusername
Name             : testname
Email            : testemail\n'''
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), info)

    def test_show_user_with_fullinfo_success(self):
        showUser(UserStub(), True)
        info = '''################ USER INFO ################
Username         : testusername
Name             : testname
Email            : testemail
Upload limit     : 0.00
Upload limit end : 01.01.1970\n'''
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), info)

    def test_show_note_success(self):
        note = '''################## TITLE ##################
testnote
=================== META ==================
Created: 01.01.1970      Updated:01.01.1970     \n'''\
'''----------------- CONTENT -----------------
Tags: tag1, tag2, tag3
##note content\n\n\n'''
        showNote(NoteStub())
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), note)

    def test_print_list_without_title_success(self):
        notes_list = '''Total found: 2
  1 : 01.01.1970  testnote
  2 : 01.01.1970  testnote\n'''
        printList([NoteStub() for _ in xrange(2)])
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), notes_list)

    def test_print_list_with_title_success(self):
        notes_list = '''=================== test ==================
Total found: 2
  1 : 01.01.1970  testnote
  2 : 01.01.1970  testnote\n'''
        printList([NoteStub() for _ in xrange(2)], title='test')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), notes_list)

    def test_print_list_with_urls_success(self):
        notes_list = '''=================== test ==================
Total found: 2
  1 : 01.01.1970  testnote >>> https://www.evernote.com/Home.action?#n=12345
  2 : 01.01.1970  testnote >>> https://www.evernote.com/Home.action?#n=12345
'''
        printList([NoteStub() for _ in xrange(2)], title='test', showUrl=True)
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), notes_list)

    def test_print_list_with_selector_success(self):
        out.rawInput = lambda x: 2
        notes_list = '''=================== test ==================
Total found: 2
  1 : 01.01.1970  testnote
  2 : 01.01.1970  testnote
  0 : -Cancel-\n'''
        out.printList([NoteStub() for _ in xrange(2)], title='test', showSelector=True)
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), notes_list)

    def test_search_result_success(self):
        result = '''Search request: test
Total found: 2
  1 : 01.01.1970  testnote
  2 : 01.01.1970  testnote\n'''
        SearchResult([NoteStub() for _ in xrange(2)], 'test')
        sys.stdout.seek(0)
        self.assertEquals(sys.stdout.read(), result)

    def test_print_date(self):
        self.assertEquals(printDate(1000000), '01.01.1970')
