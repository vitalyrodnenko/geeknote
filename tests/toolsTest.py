# -*- coding: utf-8 -*-
import unittest
from geeknote.tools import checkIsInt, strip, decodeArgs,\
    stdinEncode, stdoutEncode, Struct


class testTools(unittest.TestCase):

    def test_check_is_int_success(self):
        self.assertTrue(checkIsInt(1))

    def test_check_is_int_float_success(self):
        self.assertTrue(checkIsInt(1.1))

    def test_check_is_int_false(self):
        self.assertTrue(checkIsInt('1'))

    def test_strip_none_data_success(self):
        self.assertFalse(strip(None))

    def test_strip_dict_data_success(self):
        data = {'key \t\n\r\"\'': 'test'}
        self.assertDictEqual(strip(data), {'key': 'test'})

    def test_strip_list_data_success(self):
        data = ['key \t\n\r\"\'', 'value \t\n\r\"\'']
        self.assertListEqual(strip(data), ['key', 'value'])

    def test_strip_str_data_success(self):
        data = 'text text text \t\n\r\"\''
        self.assertEqual(strip(data), 'text text text')

    def test_strip_int_data_false(self):
        self.assertRaises(Exception, strip, 1)

    def test_struct_success(self):
        struct = Struct(key='value')
        self.assertDictEqual(struct.__dict__, {'key': 'value'})

    def test_decode_args_success(self):
        result = [1, '2', 'test', '\xc2\xae',
                  '\xd1\x82\xd0\xb5\xd1\x81\xd1\x82']
        self.assertListEqual(decodeArgs([1, '2', 'test', '®', 'тест']), result)

    def test_stdinEncode_success(self):
        self.assertEqual(stdinEncode('тест'), 'тест')
        self.assertEqual(stdinEncode('test'), 'test')
        self.assertEqual(stdinEncode('®'), '®')
        self.assertEqual(stdinEncode(1), 1)

    def test_stdoutEncode_success(self):
        self.assertEqual(stdoutEncode('тест'), 'тест')
        self.assertEqual(stdoutEncode('test'), 'test')
        self.assertEqual(stdoutEncode('®'), '®')
        self.assertEqual(stdoutEncode(1), 1)
