# -*- coding: utf-8 -*-

import os, sys
import logging
import config

if config.DEBUG:
    logging.basicConfig(format="%(filename)s %(funcName)s %(lineno)d : %(message)s", level=logging.DEBUG)
else:
    logging.basicConfig(format="%(asctime)-15s %(module)s %(funcName)s %(lineno)d : %(message)s", filename=config.ERROR_LOG)
