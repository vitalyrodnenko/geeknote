# databases/__init__.py
# Copyright (C) 2005-2012 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Include imports from the sqlalchemy.dialects package for backwards
compatibility with pre 0.6 versions.

"""
from sqlalchemy.dialects.sqlite import base as sqlite
from sqlalchemy.dialects.postgresql import base as postgresql
postgres = postgresql
from sqlalchemy.dialects.mysql import base as mysql
from sqlalchemy.dialects.drizzle import base as drizzle
from sqlalchemy.dialects.oracle import base as oracle
from sqlalchemy.dialects.firebird import base as firebird
from sqlalchemy.dialects.maxdb import base as maxdb
from sqlalchemy.dialects.informix import base as informix
from sqlalchemy.dialects.mssql import base as mssql
from sqlalchemy.dialects.access import base as access
from sqlalchemy.dialects.sybase import base as sybase


__all__ = (
    'access',
    'drizzle',
    'firebird',
    'informix',
    'maxdb',
    'mssql',
    'mysql',
    'postgresql',
    'sqlite',
    'oracle',
    'sybase',
    )
