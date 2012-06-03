# sqlite/base.py
# Copyright (C) 2005-2012 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Support for the SQLite database.

For information on connecting using a specific driver, see the documentation
section regarding that driver.

Date and Time Types
-------------------

SQLite does not have built-in DATE, TIME, or DATETIME types, and pysqlite does not provide 
out of the box functionality for translating values between Python `datetime` objects
and a SQLite-supported format.  SQLAlchemy's own :class:`~sqlalchemy.types.DateTime`
and related types provide date formatting and parsing functionality when SQlite is used.
The implementation classes are :class:`~.sqlite.DATETIME`, :class:`~.sqlite.DATE` and :class:`~.sqlite.TIME`.
These types represent dates and times as ISO formatted strings, which also nicely
support ordering.   There's no reliance on typical "libc" internals for these functions
so historical dates are fully supported.

Auto Incrementing Behavior
--------------------------

Background on SQLite's autoincrement is at: http://sqlite.org/autoinc.html

Two things to note:

* The AUTOINCREMENT keyword is **not** required for SQLite tables to
  generate primary key values automatically. AUTOINCREMENT only means that
  the algorithm used to generate ROWID values should be slightly different.
* SQLite does **not** generate primary key (i.e. ROWID) values, even for
  one column, if the table has a composite (i.e. multi-column) primary key.
  This is regardless of the AUTOINCREMENT keyword being present or not.

To specifically render the AUTOINCREMENT keyword on the primary key
column when rendering DDL, add the flag ``sqlite_autoincrement=True`` 
to the Table construct::

    Table('sometable', metadata,
            Column('id', Integer, primary_key=True), 
            sqlite_autoincrement=True)

Transaction Isolation Level
---------------------------

:func:`.create_engine` accepts an ``isolation_level`` parameter which results in 
the command ``PRAGMA read_uncommitted <level>`` being invoked for every new 
connection.   Valid values for this parameter are ``SERIALIZABLE`` and 
``READ UNCOMMITTED`` corresponding to a value of 0 and 1, respectively.
See the section :ref:`pysqlite_serializable` for an important workaround
when using serializable isolation with Pysqlite.

"""

import datetime, re

from sqlalchemy import sql, exc
from sqlalchemy.engine import default, base, reflection
from sqlalchemy import types as sqltypes
from sqlalchemy import util
from sqlalchemy.sql import compiler
from sqlalchemy import processors

from sqlalchemy.types import BLOB, BOOLEAN, CHAR, DATE, DATETIME, DECIMAL,\
    FLOAT, REAL, INTEGER, NUMERIC, SMALLINT, TEXT, TIME, TIMESTAMP, VARCHAR

class _DateTimeMixin(object):
    _reg = None
    _storage_format = None

    def __init__(self, storage_format=None, regexp=None, **kw):
        super(_DateTimeMixin, self).__init__(**kw)
        if regexp is not None:
            self._reg = re.compile(regexp)
        if storage_format is not None:
            self._storage_format = storage_format

class DATETIME(_DateTimeMixin, sqltypes.DateTime):
    """Represent a Python datetime object in SQLite using a string.
    
    The default string storage format is::
    
        "%04d-%02d-%02d %02d:%02d:%02d.%06d" % (value.year, 
                                value.month, value.day,
                                value.hour, value.minute, 
                                value.second, value.microsecond)
    
    e.g.::
    
        2011-03-15 12:05:57.10558
    
    The storage format can be customized to some degree using the 
    ``storage_format`` and ``regexp`` parameters, such as::
        
        import re
        from sqlalchemy.dialects.sqlite import DATETIME
        
        dt = DATETIME(
                storage_format="%04d/%02d/%02d %02d-%02d-%02d-%06d",
                regexp=re.compile("(\d+)/(\d+)/(\d+) (\d+)-(\d+)-(\d+)(?:-(\d+))?")
            )
    
    :param storage_format: format string which will be applied to the 
     tuple ``(value.year, value.month, value.day, value.hour,
     value.minute, value.second, value.microsecond)``, given a
     Python datetime.datetime() object.
    
    :param regexp: regular expression which will be applied to 
     incoming result rows. The resulting match object is applied to
     the Python datetime() constructor via ``*map(int,
     match_obj.groups(0))``.
    """

    _storage_format = "%04d-%02d-%02d %02d:%02d:%02d.%06d"

    def bind_processor(self, dialect):
        datetime_datetime = datetime.datetime
        datetime_date = datetime.date
        format = self._storage_format
        def process(value):
            if value is None:
                return None
            elif isinstance(value, datetime_datetime):
                return format % (value.year, value.month, value.day,
                                 value.hour, value.minute, value.second,
                                 value.microsecond)
            elif isinstance(value, datetime_date):
                return format % (value.year, value.month, value.day,
                                 0, 0, 0, 0)
            else:
                raise TypeError("SQLite DateTime type only accepts Python "
                                "datetime and date objects as input.")
        return process

    def result_processor(self, dialect, coltype):
        if self._reg:
            return processors.str_to_datetime_processor_factory(
                self._reg, datetime.datetime)
        else:
            return processors.str_to_datetime

class DATE(_DateTimeMixin, sqltypes.Date):
    """Represent a Python date object in SQLite using a string.

    The default string storage format is::
    
        "%04d-%02d-%02d" % (value.year, value.month, value.day)
    
    e.g.::
    
        2011-03-15
    
    The storage format can be customized to some degree using the 
    ``storage_format`` and ``regexp`` parameters, such as::
    
        import re
        from sqlalchemy.dialects.sqlite import DATE

        d = DATE(
                storage_format="%02d/%02d/%02d",
                regexp=re.compile("(\d+)/(\d+)/(\d+)")
            )
    
    :param storage_format: format string which will be applied to the 
     tuple ``(value.year, value.month, value.day)``,
     given a Python datetime.date() object.
    
    :param regexp: regular expression which will be applied to 
     incoming result rows. The resulting match object is applied to
     the Python date() constructor via ``*map(int,
     match_obj.groups(0))``.
     
    """

    _storage_format = "%04d-%02d-%02d"

    def bind_processor(self, dialect):
        datetime_date = datetime.date
        format = self._storage_format
        def process(value):
            if value is None:
                return None
            elif isinstance(value, datetime_date):
                return format % (value.year, value.month, value.day)
            else:
                raise TypeError("SQLite Date type only accepts Python "
                                "date objects as input.")
        return process

    def result_processor(self, dialect, coltype):
        if self._reg:
            return processors.str_to_datetime_processor_factory(
                self._reg, datetime.date)
        else:
            return processors.str_to_date

class TIME(_DateTimeMixin, sqltypes.Time):
    """Represent a Python time object in SQLite using a string.
    
    The default string storage format is::
    
        "%02d:%02d:%02d.%06d" % (value.hour, value.minute, 
                                value.second,
                                 value.microsecond)
    
    e.g.::
    
        12:05:57.10558
    
    The storage format can be customized to some degree using the 
    ``storage_format`` and ``regexp`` parameters, such as::
    
        import re
        from sqlalchemy.dialects.sqlite import TIME

        t = TIME(
                storage_format="%02d-%02d-%02d-%06d",
                regexp=re.compile("(\d+)-(\d+)-(\d+)-(?:-(\d+))?")
            )
    
    :param storage_format: format string which will be applied 
     to the tuple ``(value.hour, value.minute, value.second,
     value.microsecond)``, given a Python datetime.time() object.
    
    :param regexp: regular expression which will be applied to 
     incoming result rows. The resulting match object is applied to
     the Python time() constructor via ``*map(int,
     match_obj.groups(0))``.

    """

    _storage_format = "%02d:%02d:%02d.%06d"

    def bind_processor(self, dialect):
        datetime_time = datetime.time
        format = self._storage_format
        def process(value):
            if value is None:
                return None
            elif isinstance(value, datetime_time):
                return format % (value.hour, value.minute, value.second,
                                 value.microsecond)
            else:
                raise TypeError("SQLite Time type only accepts Python "
                                "time objects as input.")
        return process

    def result_processor(self, dialect, coltype):
        if self._reg:
            return processors.str_to_datetime_processor_factory(
                self._reg, datetime.time)
        else:
            return processors.str_to_time

colspecs = {
    sqltypes.Date: DATE,
    sqltypes.DateTime: DATETIME,
    sqltypes.Time: TIME,
}

ischema_names = {
    'BLOB': sqltypes.BLOB,
    'BOOL': sqltypes.BOOLEAN,
    'BOOLEAN': sqltypes.BOOLEAN,
    'CHAR': sqltypes.CHAR,
    'DATE': sqltypes.DATE,
    'DATETIME': sqltypes.DATETIME,
    'DECIMAL': sqltypes.DECIMAL,
    'FLOAT': sqltypes.FLOAT,
    'INT': sqltypes.INTEGER,
    'INTEGER': sqltypes.INTEGER,
    'NUMERIC': sqltypes.NUMERIC,
    'REAL': sqltypes.REAL,
    'SMALLINT': sqltypes.SMALLINT,
    'TEXT': sqltypes.TEXT,
    'TIME': sqltypes.TIME,
    'TIMESTAMP': sqltypes.TIMESTAMP,
    'VARCHAR': sqltypes.VARCHAR,
}



class SQLiteCompiler(compiler.SQLCompiler):
    extract_map = util.update_copy(
        compiler.SQLCompiler.extract_map,
        {
        'month': '%m',
        'day': '%d',
        'year': '%Y',
        'second': '%S',
        'hour': '%H',
        'doy': '%j',
        'minute': '%M',
        'epoch': '%s',
        'dow': '%w',
        'week': '%W'
    })

    def visit_now_func(self, fn, **kw):
        return "CURRENT_TIMESTAMP"

    def visit_true(self, expr, **kw):
        return '1'

    def visit_false(self, expr, **kw):
        return '0'

    def visit_char_length_func(self, fn, **kw):
        return "length%s" % self.function_argspec(fn)

    def visit_cast(self, cast, **kwargs):
        if self.dialect.supports_cast:
            return super(SQLiteCompiler, self).visit_cast(cast)
        else:
            return self.process(cast.clause)

    def visit_extract(self, extract, **kw):
        try:
            return "CAST(STRFTIME('%s', %s) AS INTEGER)" % (
                self.extract_map[extract.field], self.process(extract.expr, **kw))
        except KeyError:
            raise exc.CompileError(
                "%s is not a valid extract argument." % extract.field)

    def limit_clause(self, select):
        text = ""
        if select._limit is not None:
            text +=  "\n LIMIT " + self.process(sql.literal(select._limit))
        if select._offset is not None:
            if select._limit is None:
                text += "\n LIMIT " + self.process(sql.literal(-1))
            text += " OFFSET " + self.process(sql.literal(select._offset))
        else:
            text += " OFFSET " + self.process(sql.literal(0))
        return text

    def for_update_clause(self, select):
        # sqlite has no "FOR UPDATE" AFAICT
        return ''


class SQLiteDDLCompiler(compiler.DDLCompiler):

    def get_column_specification(self, column, **kwargs):
        colspec = self.preparer.format_column(column) + " " + self.dialect.type_compiler.process(column.type)
        default = self.get_column_default_string(column)
        if default is not None:
            colspec += " DEFAULT " + default

        if not column.nullable:
            colspec += " NOT NULL"

        if column.primary_key and \
             column.table.kwargs.get('sqlite_autoincrement', False) and \
             len(column.table.primary_key.columns) == 1 and \
             issubclass(column.type._type_affinity, sqltypes.Integer) and \
             not column.foreign_keys:
             colspec += " PRIMARY KEY AUTOINCREMENT"

        return colspec

    def visit_primary_key_constraint(self, constraint):
        # for columns with sqlite_autoincrement=True,
        # the PRIMARY KEY constraint can only be inline
        # with the column itself.
        if len(constraint.columns) == 1:
            c = list(constraint)[0]
            if c.primary_key and \
                c.table.kwargs.get('sqlite_autoincrement', False) and \
                issubclass(c.type._type_affinity, sqltypes.Integer) and \
                not c.foreign_keys:
                return None
 
        return super(SQLiteDDLCompiler, self).\
                    visit_primary_key_constraint(constraint)

    def visit_foreign_key_constraint(self, constraint):

        local_table = constraint._elements.values()[0].parent.table
        remote_table = list(constraint._elements.values())[0].column.table

        if local_table.schema != remote_table.schema:
            return None
        else:
            return super(SQLiteDDLCompiler, self).visit_foreign_key_constraint(constraint)

    def define_constraint_remote_table(self, constraint, table, preparer):
        """Format the remote table clause of a CREATE CONSTRAINT clause."""

        return preparer.format_table(table, use_schema=False)

    def visit_create_index(self, create):
        index = create.element
        preparer = self.preparer
        text = "CREATE "
        if index.unique:
            text += "UNIQUE "
        text += "INDEX %s ON %s (%s)" \
                    % (preparer.format_index(index,
                       name=self._index_identifier(index.name)),
                       preparer.format_table(index.table, use_schema=False),
                       ', '.join(preparer.quote(c.name, c.quote)
                                 for c in index.columns))
        return text

class SQLiteTypeCompiler(compiler.GenericTypeCompiler):
    def visit_large_binary(self, type_):
        return self.visit_BLOB(type_)

class SQLiteIdentifierPreparer(compiler.IdentifierPreparer):
    reserved_words = set([
        'add', 'after', 'all', 'alter', 'analyze', 'and', 'as', 'asc',
        'attach', 'autoincrement', 'before', 'begin', 'between', 'by',
        'cascade', 'case', 'cast', 'check', 'collate', 'column', 'commit',
        'conflict', 'constraint', 'create', 'cross', 'current_date',
        'current_time', 'current_timestamp', 'database', 'default',
        'deferrable', 'deferred', 'delete', 'desc', 'detach', 'distinct',
        'drop', 'each', 'else', 'end', 'escape', 'except', 'exclusive',
        'explain', 'false', 'fail', 'for', 'foreign', 'from', 'full', 'glob',
        'group', 'having', 'if', 'ignore', 'immediate', 'in', 'index',
        'indexed', 'initially', 'inner', 'insert', 'instead', 'intersect', 'into', 'is',
        'isnull', 'join', 'key', 'left', 'like', 'limit', 'match', 'natural',
        'not', 'notnull', 'null', 'of', 'offset', 'on', 'or', 'order', 'outer',
        'plan', 'pragma', 'primary', 'query', 'raise', 'references',
        'reindex', 'rename', 'replace', 'restrict', 'right', 'rollback',
        'row', 'select', 'set', 'table', 'temp', 'temporary', 'then', 'to',
        'transaction', 'trigger', 'true', 'union', 'unique', 'update', 'using',
        'vacuum', 'values', 'view', 'virtual', 'when', 'where',
        ])

    def format_index(self, index, use_schema=True, name=None):
        """Prepare a quoted index and schema name."""

        if name is None:
            name = index.name
        result = self.quote(name, index.quote)
        if not self.omit_schema and use_schema and getattr(index.table, "schema", None):
            result = self.quote_schema(index.table.schema, index.table.quote_schema) + "." + result
        return result

class SQLiteExecutionContext(default.DefaultExecutionContext):
    @util.memoized_property
    def _preserve_raw_colnames(self):
        return self.execution_options.get("sqlite_raw_colnames", False)

    def _translate_colname(self, colname):
        # adjust for dotted column names.  SQLite
        # in the case of UNION may store col names as 
        # "tablename.colname"
        # in cursor.description
        if not self._preserve_raw_colnames  and "." in colname:
            return colname.split(".")[1], colname
        else:
            return colname, None


class SQLiteDialect(default.DefaultDialect):
    name = 'sqlite'
    supports_alter = False
    supports_unicode_statements = True
    supports_unicode_binds = True
    supports_default_values = True
    supports_empty_insert = False
    supports_cast = True

    default_paramstyle = 'qmark'
    execution_ctx_cls = SQLiteExecutionContext
    statement_compiler = SQLiteCompiler
    ddl_compiler = SQLiteDDLCompiler
    type_compiler = SQLiteTypeCompiler
    preparer = SQLiteIdentifierPreparer
    ischema_names = ischema_names
    colspecs = colspecs
    isolation_level = None

    supports_cast = True
    supports_default_values = True

    def __init__(self, isolation_level=None, native_datetime=False, **kwargs):
        default.DefaultDialect.__init__(self, **kwargs)
        self.isolation_level = isolation_level

        # this flag used by pysqlite dialect, and perhaps others in the
        # future, to indicate the driver is handling date/timestamp
        # conversions (and perhaps datetime/time as well on some 
        # hypothetical driver ?)
        self.native_datetime = native_datetime

        if self.dbapi is not None:
            self.supports_default_values = \
                                self.dbapi.sqlite_version_info >= (3, 3, 8)
            self.supports_cast = \
                                self.dbapi.sqlite_version_info >= (3, 2, 3)

    _isolation_lookup = {
        'READ UNCOMMITTED':1,
        'SERIALIZABLE':0
    }
    def set_isolation_level(self, connection, level):
        try:
            isolation_level = self._isolation_lookup[level.replace('_', ' ')]
        except KeyError:
            raise exc.ArgumentError(
                "Invalid value '%s' for isolation_level. "
                "Valid isolation levels for %s are %s" % 
                (level, self.name, ", ".join(self._isolation_lookup))
                ) 
        cursor = connection.cursor()
        cursor.execute("PRAGMA read_uncommitted = %d" % isolation_level)
        cursor.close()

    def get_isolation_level(self, connection):
        cursor = connection.cursor()
        cursor.execute('PRAGMA read_uncommitted')
        res = cursor.fetchone()
        if res:
            value = res[0]
        else: 
            # http://www.sqlite.org/changes.html#version_3_3_3
            # "Optional READ UNCOMMITTED isolation (instead of the 
            # default isolation level of SERIALIZABLE) and 
            # table level locking when database connections 
            # share a common cache.""
            # pre-SQLite 3.3.0 default to 0
            value = 0
        cursor.close()
        if value == 0:
            return "SERIALIZABLE"
        elif value == 1:
            return "READ UNCOMMITTED"
        else:
            assert False, "Unknown isolation level %s" % value

    def on_connect(self):
        if self.isolation_level is not None:
            def connect(conn):
                self.set_isolation_level(conn, self.isolation_level)
            return connect
        else:
            return None

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        if schema is not None:
            qschema = self.identifier_preparer.quote_identifier(schema)
            master = '%s.sqlite_master' % qschema
            s = ("SELECT name FROM %s "
                 "WHERE type='table' ORDER BY name") % (master,)
            rs = connection.execute(s)
        else:
            try:
                s = ("SELECT name FROM "
                     " (SELECT * FROM sqlite_master UNION ALL "
                     "  SELECT * FROM sqlite_temp_master) "
                     "WHERE type='table' ORDER BY name")
                rs = connection.execute(s)
            except exc.DBAPIError:
                s = ("SELECT name FROM sqlite_master "
                     "WHERE type='table' ORDER BY name")
                rs = connection.execute(s)

        return [row[0] for row in rs]

    def has_table(self, connection, table_name, schema=None):
        quote = self.identifier_preparer.quote_identifier
        if schema is not None:
            pragma = "PRAGMA %s." % quote(schema)
        else:
            pragma = "PRAGMA "
        qtable = quote(table_name)
        cursor = _pragma_cursor(connection.execute("%stable_info(%s)" % (pragma, qtable)))
        row = cursor.fetchone()

        # consume remaining rows, to work around
        # http://www.sqlite.org/cvstrac/tktview?tn=1884
        while not cursor.closed and cursor.fetchone() is not None:
            pass

        return (row is not None)

    @reflection.cache
    def get_view_names(self, connection, schema=None, **kw):
        if schema is not None:
            qschema = self.identifier_preparer.quote_identifier(schema)
            master = '%s.sqlite_master' % qschema
            s = ("SELECT name FROM %s "
                 "WHERE type='view' ORDER BY name") % (master,)
            rs = connection.execute(s)
        else:
            try:
                s = ("SELECT name FROM "
                     " (SELECT * FROM sqlite_master UNION ALL "
                     "  SELECT * FROM sqlite_temp_master) "
                     "WHERE type='view' ORDER BY name")
                rs = connection.execute(s)
            except exc.DBAPIError:
                s = ("SELECT name FROM sqlite_master "
                     "WHERE type='view' ORDER BY name")
                rs = connection.execute(s)

        return [row[0] for row in rs]

    @reflection.cache
    def get_view_definition(self, connection, view_name, schema=None, **kw):
        quote = self.identifier_preparer.quote_identifier
        if schema is not None:
            qschema = self.identifier_preparer.quote_identifier(schema)
            master = '%s.sqlite_master' % qschema
            s = ("SELECT sql FROM %s WHERE name = '%s'"
                 "AND type='view'") % (master, view_name)
            rs = connection.execute(s)
        else:
            try:
                s = ("SELECT sql FROM "
                     " (SELECT * FROM sqlite_master UNION ALL "
                     "  SELECT * FROM sqlite_temp_master) "
                     "WHERE name = '%s' "
                     "AND type='view'") % view_name
                rs = connection.execute(s)
            except exc.DBAPIError:
                s = ("SELECT sql FROM sqlite_master WHERE name = '%s' "
                     "AND type='view'") % view_name
                rs = connection.execute(s)

        result = rs.fetchall()
        if result:
            return result[0].sql

    @reflection.cache
    def get_columns(self, connection, table_name, schema=None, **kw):
        quote = self.identifier_preparer.quote_identifier
        if schema is not None:
            pragma = "PRAGMA %s." % quote(schema)
        else:
            pragma = "PRAGMA "
        qtable = quote(table_name)
        c = _pragma_cursor(
                    connection.execute("%stable_info(%s)" % 
                    (pragma, qtable)))
        found_table = False
        columns = []
        while True:
            row = c.fetchone()
            if row is None:
                break
            (name, type_, nullable, default, has_default, primary_key) = \
                (row[1], row[2].upper(), not row[3], 
                row[4], row[4] is not None, row[5])
            name = re.sub(r'^\"|\"$', '', name)
            match = re.match(r'(\w+)(\(.*?\))?', type_)
            if match:
                coltype = match.group(1)
                args = match.group(2)
            else:
                coltype = "VARCHAR"
                args = ''
            try:
                coltype = self.ischema_names[coltype]
                if args is not None:
                    args = re.findall(r'(\d+)', args)
                    coltype = coltype(*[int(a) for a in args])
            except KeyError:
                util.warn("Did not recognize type '%s' of column '%s'" %
                          (coltype, name))
                coltype = sqltypes.NullType()

            columns.append({
                'name' : name,
                'type' : coltype,
                'nullable' : nullable,
                'default' : default,
                'autoincrement':default is None,
                'primary_key': primary_key
            })
        return columns

    @reflection.cache
    def get_primary_keys(self, connection, table_name, schema=None, **kw):
        cols = self.get_columns(connection, table_name, schema, **kw)
        pkeys = []
        for col in cols:
            if col['primary_key']:
                pkeys.append(col['name'])
        return pkeys

    @reflection.cache
    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        quote = self.identifier_preparer.quote_identifier
        if schema is not None:
            pragma = "PRAGMA %s." % quote(schema)
        else:
            pragma = "PRAGMA "
        qtable = quote(table_name)
        c = _pragma_cursor(connection.execute("%sforeign_key_list(%s)" % (pragma, qtable)))
        fkeys = []
        fks = {}
        while True:
            row = c.fetchone()
            if row is None:
                break
            (numerical_id, rtbl, lcol, rcol) = (row[0], row[2], row[3], row[4])
            # sqlite won't return rcol if the table
            # was created with REFERENCES <tablename>, no col
            if rcol is None:
                rcol = lcol
            rtbl = re.sub(r'^\"|\"$', '', rtbl)
            lcol = re.sub(r'^\"|\"$', '', lcol)
            rcol = re.sub(r'^\"|\"$', '', rcol)
            try:
                fk = fks[numerical_id]
            except KeyError:
                fk = {
                    'name' : None,
                    'constrained_columns' : [],
                    'referred_schema' : None,
                    'referred_table' : rtbl,
                    'referred_columns' : []
                }
                fkeys.append(fk)
                fks[numerical_id] = fk

            # look up the table based on the given table's engine, not 'self',
            # since it could be a ProxyEngine
            if lcol not in fk['constrained_columns']:
                fk['constrained_columns'].append(lcol)
            if rcol not in fk['referred_columns']:
                fk['referred_columns'].append(rcol)
        return fkeys

    @reflection.cache
    def get_indexes(self, connection, table_name, schema=None, **kw):
        quote = self.identifier_preparer.quote_identifier
        if schema is not None:
            pragma = "PRAGMA %s." % quote(schema)
        else:
            pragma = "PRAGMA "
        include_auto_indexes = kw.pop('include_auto_indexes', False)
        qtable = quote(table_name)
        c = _pragma_cursor(connection.execute("%sindex_list(%s)" % (pragma, qtable)))
        indexes = []
        while True:
            row = c.fetchone()
            if row is None:
                break
            # ignore implicit primary key index.
            # http://www.mail-archive.com/sqlite-users@sqlite.org/msg30517.html
            elif not include_auto_indexes and row[1].startswith('sqlite_autoindex'):
                continue

            indexes.append(dict(name=row[1], column_names=[], unique=row[2]))
        # loop thru unique indexes to get the column names.
        for idx in indexes:
            c = connection.execute("%sindex_info(%s)" % (pragma, quote(idx['name'])))
            cols = idx['column_names']
            while True:
                row = c.fetchone()
                if row is None:
                    break
                cols.append(row[2])
        return indexes


def _pragma_cursor(cursor):
    """work around SQLite issue whereby cursor.description 
    is blank when PRAGMA returns no rows."""

    if cursor.closed:
        cursor.fetchone = lambda: None
    return cursor
