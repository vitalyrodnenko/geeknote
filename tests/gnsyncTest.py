#-*- encoding: utf-8 -*-
import unittest
from geeknote.gnsync import remove_control_characters

class testGnsync(unittest.TestCase):
    def setUp(self):
        self.given_eng = '\0This is an english\1 sentence. Is it ok?'
        self.expected_eng = 'This is an english sentence. Is it ok?'
        self.given_kor = '한국\2어입니\3다. 잘 되나요?'
        self.expected_kor = '한국어입니다. 잘 되나요?'
        self.given_chn = '中\4国的输入。我令\5您着迷？'
        self.expected_chn = '中国的输入。我令您着迷？'
        self.given_combined = self.expected_combined = """# 제목

## 제 1 장

_한국어 입력입니다. 잘 되나요?_

## 第 2 章

*中国的输入。我令您着迷？*

## Chapter 3

- May the force be with you!

"""

    def test_strip_eng(self):
        self.assertEqual(remove_control_characters(self.given_eng.decode('utf-8')).encode('utf-8'),
                         self.expected_eng)
                         
    def test_strip_kor(self):
        self.assertEqual(remove_control_characters(self.given_kor.decode('utf-8')).encode('utf-8'),
                         self.expected_kor)

    def test_strip_chn(self):
        self.assertEqual(remove_control_characters(self.given_chn.decode('utf-8')).encode('utf-8'),
                         self.expected_chn)

    def test_strip_nochange(self):
        self.assertEqual(remove_control_characters(self.given_combined.decode('utf-8')).encode('utf-8'),
                         self.expected_combined)
