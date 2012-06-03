# access/base.py
# Copyright (C) 2007-2011 the SQLAlchemy authors and contributors <see AUTHORS file>
# Copyright (C) 2007 Paul Johnston, paj@pajhome.org.uk
# Portions derived from jet2sql.py by Matt Keranen, mksql@yahoo.com
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
Support for the Microsoft Access database.

This dialect is *not* ported to SQLAlchemy 0.6 or 0.7.

This dialect is *not* tested on SQLAlchemy 0.6 or 0.7.


"""
from sqlalchemy import sql, schema, types, exc, pool
from sqlalchemy.sql import compiler, expression
from sqlalchemy.engine import default, base, reflection
from sqlalchemy import processors

class AcNumeric(types.Numeric):
    def get_col_spec(self):
        return "NUMERIC"

    def bind_processor(self, dialect):
        return processors.to_str

    def result_processor(self, dialect, coltype):
        return None

class AcFloat(types.Float):
    def get_col_spec(self):
        return "FLOAT"

    def bind_processor(self, dialect):
        """By converting to string, we can use Decimal types round-trip."""
        return processors.to_str

class AcInteger(types.Integer):
    def get_col_spec(self):
        return "INTEGER"

class AcTinyInteger(types.Integer):
    def get_col_spec(self):
        return "TINYINT"

class AcSmallInteger(types.SmallInteger):
    def get_col_spec(self):
        return "SMALLINT"

class AcDateTime(types.DateTime):
    def get_col_spec(self):
        return "DATETIME"

class AcDate(types.Date):

    def get_col_spec(self):
        return "DATETIME"

class AcText(types.Text):
    def get_col_spec(self):
        return "MEMO"

class AcString(types.String):
    def get_col_spec(self):
        return "TEXT" + (self.length and ("(%d)" % self.length) or "")

class AcUnicode(types.Unicode):
    def get_col_spec(self):
        return "TEXT" + (self.length and ("(%d)" % self.length) or "")

    def bind_processor(self, dialect):
        return None

    def result_processor(self, dialect, coltype):
        return None

class AcChar(types.CHAR):
    def get_col_spec(self):
        return "TEXT" + (self.length and ("(%d)" % self.length) or "")

class AcBinary(types.LargeBinary):
    def get_col_spec(self):
        return "BINARY"

class AcBoolean(types.Boolean):
    def get_col_spec(self):
        return "YESNO"

class AcTimeStamp(types.TIMESTAMP):
    def get_col_spec(self):
        return "TIMESTAMP"

class AccessExecutionContext(default.DefaultExecutionContext):
    def _has_implicit_sequence(self, column):
        if column.primary_key and column.autoincrement:
            if isinstance(column.type, types.Integer) and \
                not column.foreign_keys:
                if column.default is None or \
                        (isinstance(column.default, schema.Sequence) and \
                                column.default.optional):
                    return True
        return False

    def post_exec(self):
        """If we inserted into a row with a COUNTER column, fetch the ID"""

        if self.compiled.isinsert:
            tbl = self.compiled.statement.table
            if not hasattr(tbl, 'has_sequence'):
                tbl.has_sequence = None
                for column in tbl.c:
                    if getattr(column, 'sequence', False) or \
                        self._has_implicit_sequence(column):
                        tbl.has_sequence = column
                        break

            if bool(tbl.has_sequence):
                # TBD: for some reason _last_inserted_ids doesn't exist here
                # (but it does at corresponding point in mssql???)
                #if not len(self._last_inserted_ids) or
                # self._last_inserted_ids[0] is None:
                self.cursor.execute("SELECT @@identity AS lastrowid")
                row = self.cursor.fetchone()
                self._last_inserted_ids = [int(row[0])] 
                #+ self._last_inserted_ids[1:]
                # print "LAST ROW ID", self._last_inserted_ids

        super(AccessExecutionContext, self).post_exec()


const, daoEngine = None, None
class AccessDialect(default.DefaultDialect):
    colspecs = {
        types.Unicode : AcUnicode,
        types.Integer : AcInteger,
        types.SmallInteger: AcSmallInteger,
        types.Numeric : AcNumeric,
        types.Float : AcFloat,
        types.DateTime : AcDateTime,
        types.Date : AcDate,
        types.String : AcString,
        types.LargeBinary : AcBinary,
        types.Boolean : AcBoolean,
        types.Text : AcText,
        types.CHAR: AcChar,
        types.TIMESTAMP: AcTimeStamp,
    }
    name = 'access'
    supports_sane_rowcount = False
    supports_sane_multi_rowcount = False

    ported_sqla_06 = False

    def type_descriptor(self, typeobj):
        newobj = types.adapt_type(typeobj, self.colspecs)
        return newobj

    def __init__(self, **params):
        super(AccessDialect, self).__init__(**params)
        self.text_as_varchar = False
        self._dtbs = None

    @classmethod
    def dbapi(cls):
        import win32com.client, pythoncom

        global const, daoEngine
        if const is None:
            const = win32com.client.constants
            for suffix in (".36", ".35", ".30"):
                try:
                    daoEngine = win32com.client.\
                                gencache.\
                                EnsureDispatch("DAO.DBEngine" + suffix)
                    break
                except pythoncom.com_error:
                    pass
            else:
                raise exc.InvalidRequestError(
                        "Can't find a DB engine. Check "
                        "http://support.microsoft.com/kb/239114 for details.")

        import pyodbc as module
        return module

    def create_connect_args(self, url):
        opts = url.translate_connect_args()
        connectors = ["Driver={Microsoft Access Driver (*.mdb)}"]
        connectors.append("Dbq=%s" % opts["database"])
        user = opts.get("username", None)
        if user:
            connectors.append("UID=%s" % user)
            connectors.append("PWD=%s" % opts.get("password", ""))
        return [[";".join(connectors)], {}]

    def last_inserted_ids(self):
        return self.context.last_inserted_ids

    def do_execute(self, cursor, statement, params, context=None):
        if params == {}:
            params = ()
        super(AccessDialect, self).\
                    do_execute(cursor, statement, params, **kwargs)

    def _execute(self, c, statement, parameters):
        try:
            if parameters == {}:
                parameters = ()
            c.execute(statement, parameters)
            self.context.rowcount = c.rowcount
        except Exception, e:
            raise exc.DBAPIError.instance(statement, parameters, e)

    def has_table(self, connection, tablename, schema=None):
        # This approach seems to be more reliable that using DAO
        try:
            connection.execute('select top 1 * from [%s]' % tablename)
            return True
        except Exception, e:
            return False

    def reflecttable(self, connection, table, include_columns):
        # This is defined in the function, as it relies on win32com constants,
        # that aren't imported until dbapi method is called
        if not hasattr(self, 'ischema_names'):
            self.ischema_names = {
                const.dbByte:       AcBinary,
                const.dbInteger:    AcInteger,
                const.dbLong:       AcInteger,
                const.dbSingle:     AcFloat,
                const.dbDouble:     AcFloat,
                const.dbDate:       AcDateTime,
                const.dbLongBinary: AcBinary,
                const.dbMemo:       AcText,
                const.dbBoolean:    AcBoolean,
                const.dbText:       AcUnicode, # All Access strings are
                                               # unicode
                const.dbCurrency:   AcNumeric,
            }

        # A fresh DAO connection is opened for each reflection
        # This is necessary, so we get the latest updates
        dtbs = daoEngine.OpenDatabase(connection.engine.url.database)

        try:
            for tbl in dtbs.TableDefs:
                if tbl.Name.lower() == table.name.lower():
                    break
            else:
                raise exc.NoSuchTableError(table.name)

            for col in tbl.Fields:
                coltype = self.ischema_names[col.Type]
                if col.Type == const.dbText:
                    coltype = coltype(col.Size)

                colargs = \
                {
                    'nullable': not(col.Required or 
                                    col.Attributes & const.dbAutoIncrField),
                }
                default = col.DefaultValue

                if col.Attributes & const.dbAutoIncrField:
                    colargs['default'] = schema.Sequence(col.Name + '_seq')
                elif default:
                    if col.Type == const.dbBoolean:
                        default = default == 'Yes' and '1' or '0'
                    colargs['server_default'] = \
                            schema.DefaultClause(sql.text(default))

                table.append_column(
                        schema.Column(col.Name, coltype, **colargs))

                # TBD: check constraints

            # Find primary key columns first
            for idx in tbl.Indexes:
                if idx.Primary:
                    for col in idx.Fields:
                        thecol = table.c[col.Name]
                        table.primary_key.add(thecol)
                        if isinstance(thecol.type, AcInteger) and \
                                not (thecol.default and
                                isinstance(
                                        thecol.default.arg, 
                                        schema.Sequence
                                )):
                            thecol.autoincrement = False

            # Then add other indexes
            for idx in tbl.Indexes:
                if not idx.Primary:
                    if len(idx.Fields) == 1:
                        col = table.c[idx.Fields[0].Name]
                        if not col.primary_key:
                            col.index = True
                            col.unique = idx.Unique
                    else:
                        pass # TBD: multi-column indexes


            for fk in dtbs.Relations:
                if fk.ForeignTable != table.name:
                    continue
                scols = [c.ForeignName for c in fk.Fields]
                rcols = ['%s.%s' % (fk.Table, c.Name) for c in fk.Fields]
                table.append_constraint(
                        schema.ForeignKeyConstraint(scols, rcols,\
                                                link_to_name=True))

        finally:
            dtbs.Close()

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        # A fresh DAO connection is opened for each reflection
        # This is necessary, so we get the latest updates
        dtbs = daoEngine.OpenDatabase(connection.engine.url.database)

        names = [t.Name for t in dtbs.TableDefs 
                if t.Name[:4] != "MSys" and t.Name[:4] != "~TMP"]
        dtbs.Close()
        return names


class AccessCompiler(compiler.SQLCompiler):
    extract_map = compiler.SQLCompiler.extract_map.copy()
    extract_map.update ({
            'month': 'm',
            'day': 'd',
            'year': 'yyyy',
            'second': 's',
            'hour': 'h',
            'doy': 'y',
            'minute': 'n',
            'quarter': 'q',
            'dow': 'w',
            'week': 'ww'
    })

    def visit_select_precolumns(self, select):
        """Access puts TOP, it's version of LIMIT here """
        s = select.distinct and "DISTINCT " or ""
        if select.limit:
            s += "TOP %s " % (select.limit)
        if select.offset:
            raise exc.InvalidRequestError(
                    'Access does not support LIMIT with an offset')
        return s

    def limit_clause(self, select):
        """Limit in access is after the select keyword"""
        return ""

    def binary_operator_string(self, binary):
        """Access uses "mod" instead of "%" """
        return binary.operator == '%' and 'mod' or binary.operator

    def label_select_column(self, select, column, asfrom):
        if isinstance(column, expression.Function):
            return column.label()
        else:
            return super(AccessCompiler, self).\
                        label_select_column(select, column, asfrom)

    function_rewrites =  {'current_date':       'now',
                          'current_timestamp':  'now',
                          'length':             'len',
                          }
    def visit_function(self, func):
        """Access function names differ from the ANSI SQL names; 
        rewrite common ones"""
        func.name = self.function_rewrites.get(func.name, func.name)
        return super(AccessCompiler, self).visit_function(func)

    def for_update_clause(self, select):
        """FOR UPDATE is not supported by Access; silently ignore"""
        return ''

    # Strip schema
    def visit_table(self, table, asfrom=False, **kwargs):
        if asfrom:
            return self.preparer.quote(table.name, table.quote)
        else:
            return ""

    def visit_join(self, join, asfrom=False, **kwargs):
        return (self.process(join.left, asfrom=True) + \
                (join.isouter and " LEFT OUTER JOIN " or " INNER JOIN ") + \
                self.process(join.right, asfrom=True) + " ON " + \
                self.process(join.onclause))

    def visit_extract(self, extract, **kw):
        field = self.extract_map.get(extract.field, extract.field)
        return 'DATEPART("%s", %s)' % \
                    (field, self.process(extract.expr, **kw))

class AccessDDLCompiler(compiler.DDLCompiler):
    def get_column_specification(self, column, **kwargs):
        colspec = self.preparer.format_column(column) + " " + \
                    column.type.dialect_impl(self.dialect).get_col_spec()

        # install a sequence if we have an implicit IDENTITY column
        if (not getattr(column.table, 'has_sequence', False)) and \
                column.primary_key and \
                column.autoincrement and \
                isinstance(column.type, types.Integer) and \
                not column.foreign_keys:
            if column.default is None or \
                (isinstance(column.default, schema.Sequence) and
                 column.default.optional):
                column.sequence = schema.Sequence(column.name + '_seq')

        if not column.nullable:
            colspec += " NOT NULL"

        if hasattr(column, 'sequence'):
            column.table.has_sequence = column
            colspec = self.preparer.format_column(column) + " counter"
        else:
            default = self.get_column_default_string(column)
            if default is not None:
                colspec += " DEFAULT " + default

        return colspec

    def visit_drop_index(self, drop):
        index = drop.element
        self.append("\nDROP INDEX [%s].[%s]" % \
                        (index.table.name,
                        self._index_identifier(index.name)))

class AccessIdentifierPreparer(compiler.IdentifierPreparer):
    reserved_words = compiler.RESERVED_WORDS.copy()
    reserved_words.update(['value', 'text'])
    def __init__(self, dialect):
        super(AccessIdentifierPreparer, self).\
                __init__(dialect, initial_quote='[', final_quote=']')


dialect = AccessDialect
dialect.poolclass = pool.SingletonThreadPool
dialect.statement_compiler = AccessCompiler
dialect.ddlcompiler = AccessDDLCompiler
dialect.preparer = AccessIdentifierPreparer
dialect.execution_ctx_cls = AccessExecutionContext
