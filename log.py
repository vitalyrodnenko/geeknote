# -*- coding: utf-8 -*-

import os, sys

# path to libs in unix systems
sys.path.append( os.path.join('/', 'usr', 'local', 'lib', 'geeknone'))

import logging

FORMAT = "%(asctime)-15s %(module)s : %(message)s"
DEBUG_FORMAT = "%(filename)s %(funcName)s %(lineno)d : %(message)s"

# logging.basicConfig(format=DEBUG_FORMAT, level=logging.DEBUG)
logging.basicConfig(format=FORMAT)