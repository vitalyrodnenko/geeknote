# -*- coding: utf-8 -*-

import logging
import config

if config.DEBUG:
    FORMAT = "%(filename)s %(funcName)s %(lineno)d : %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
else:
    FORMAT = "%(asctime)-15s %(module)s %(funcName)s %(lineno)d : %(message)s"
    logging.basicConfig(format=FORMAT, filename=config.ERROR_LOG)
