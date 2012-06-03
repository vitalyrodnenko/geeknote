# sql/compiler.py
# Copyright (C) 2005-2012 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Base SQL and DDL compiler implementations.

Classes provided include:

:class:`~sqlalchemy.sql.compiler.SQLCompiler` - renders SQL
strings

:class:`~sqlalchemy.sql.compiler.DDLCompiler` - renders DDL
(data definition language) strings

:class:`~sqlalchemy.sql.compiler.GenericTypeCompiler` - renders
type specification strings.

To generate user-defined SQL strings, see 
:module:`~sqlalchemy.ext.compiler`.

"""

import re
import sys
from sqlalchemy import schema, engine, util, exc
from sqlalchemy.sql import operators, functions, util as sql_util, \
    visitors
from sqlalchemy.sql import expression as sql
import decimal

RESERVED_WORDS = set([
    'all', 'analyse', 'analyze', 'and', 'any', 'array',
    'as', 'asc', 'asymmetric', 'authorization', 'between',
    'binary', 'both', 'case', 'cast', 'check', 'collate',
    'column', 'constraint', 'create', 'cross', 'current_date',
    'current_role', 'current_time', 'current_timestamp',
    'current_user', 'default', 'deferrable', 'desc',
    'distinct', 'do', 'else', 'end', 'except', 'false',
    'for', 'foreign', 'freeze', 'from', 'full', 'grant',
    'group', 'having', 'ilike', 'in', 'initially', 'inner',
    'intersect', 'into', 'is', 'isnull', 'join', 'leading',
    'left', 'like', 'limit', 'localtime', 'localtimestamp',
    'natural', 'new', 'not', 'notnull', 'null', 'off', 'offset',
    'old', 'on', 'only', 'or', 'order', 'outer', 'overlaps',
    'placing', 'primary', 'references', 'right', 'select',
    'session_user', 'set', 'similar', 'some', 'symmetric', 'table',
    'then', 'to', 'trailing', 'true', 'union', 'unique', 'user',
    'using', 'verbose', 'when', 'where'])

LEGAL_CHARACTERS = re.compile(r'^[A-Z0-9_$]+$', re.I)
ILLEGAL_INITIAL_CHARACTERS = set([str(x) for x in xrange(0, 10)]).union(['$'])

BIND_PARAMS = re.compile(r'(?<![:\w\$\x5c]):([\w\$]+)(?![:\w\$])', re.UNICODE)
BIND_PARAMS_ESC = re.compile(r'\x5c(:[\w\$]+)(?![:\w\$])', re.UNICODE)

BIND_TEMPLATES = {
    'pyformat':"%%(%(name)s)s",
    'qmark':"?",
    'format':"%%s",
    'numeric':":%(position)s",
    'named':":%(name)s"
}


OPERATORS =  {
    # binary
    operators.and_ : ' AND ',
    operators.or_ : ' OR ',
    operators.add : ' + ',
    operators.mul : ' * ',
    operators.sub : ' - ',
    # Py2K
    operators.div : ' / ',
    # end Py2K
    operators.mod : ' % ',
    operators.truediv : ' / ',
    operators.neg : '-',
    operators.lt : ' < ',
    operators.le : ' <= ',
    operators.ne : ' != ',
    operators.gt : ' > ',
    operators.ge : ' >= ',
    operators.eq : ' = ',
    operators.concat_op : ' || ',
    operators.between_op : ' BETWEEN ',
    operators.match_op : ' MATCH ',
    operators.in_op : ' IN ',
    operators.notin_op : ' NOT IN ',
    operators.comma_op : ', ',
    operators.from_ : ' FROM ',
    operators.as_ : ' AS ',
    operators.is_ : ' IS ',
    operators.isnot : ' IS NOT ',
    operators.collate : ' COLLATE ',

    # unary
    operators.exists : 'EXISTS ',
    operators.distinct_op : 'DISTINCT ',
    operators.inv : 'NOT ',

    # modifiers
    operators.desc_op : ' DESC',
    operators.asc_op : ' ASC',
    operators.nullsfirst_op : ' NULLS FIRST',
    operators.nullslast_op : ' NULLS LAST',
}

FUNCTIONS = {
    functions.coalesce : 'coalesce%(expr)s',
    functions.current_date: 'CURRENT_DATE',
    functions.current_time: 'CURRENT_TIME',
    functions.current_timestamp: 'CURRENT_TIMESTAMP',
    functions.current_user: 'CURRENT_USER',
    functions.localtime: 'LOCALTIME',
    functions.localtimestamp: 'LOCALTIMESTAMP',
    functions.random: 'random%(expr)s',
    functions.sysdate: 'sysdate',
    functions.session_user :'SESSION_USER',
    functions.user: 'USER'
}

EXTRACT_MAP = {
    'month': 'month',
    'day': 'day',
    'year': 'year',
    'second': 'second',
    'hour': 'hour',
    'doy': 'doy',
    'minute': 'minute',
    'quarter': 'quarter',
    'dow': 'dow',
    'week': 'week',
    'epoch': 'epoch',
    'milliseconds': 'milliseconds',
    'microseconds': 'microseconds',
    'timezone_hour': 'timezone_hour',
    'timezone_minute': 'timezone_minute'
}

COMPOUND_KEYWORDS = {
    sql.CompoundSelect.UNION : 'UNION',
    sql.CompoundSelect.UNION_ALL : 'UNION ALL',
    sql.CompoundSelect.EXCEPT : 'EXCEPT',
    sql.CompoundSelect.EXCEPT_ALL : 'EXCEPT ALL',
    sql.CompoundSelect.INTERSECT : 'INTERSECT',
    sql.CompoundSelect.INTERSECT_ALL : 'INTERSECT ALL'
}

class _CompileLabel(visitors.Visitable):
    """lightweight label object which acts as an expression._Label."""

    __visit_name__ = 'label'
    __slots__ = 'element', 'name'

    def __init__(self, col, name, alt_names=()):
        self.element = col
        self.name = name
        self._alt_names = alt_names

    @property
    def proxy_set(self):
        return self.element.proxy_set

    @property
    def type(self):
        return self.element.type

    @property
    def quote(self):
        return self.element.quote

class SQLCompiler(engine.Compiled):
    """Default implementation of Compiled.

    Compiles ClauseElements into SQL strings.   Uses a similar visit
    paradigm as visitors.ClauseVisitor but implements its own traversal.

    """

    extract_map = EXTRACT_MAP

    compound_keywords = COMPOUND_KEYWORDS

    isdelete = isinsert = isupdate = False
    """class-level defaults which can be set at the instance
    level to define if this Compiled instance represents
    INSERT/UPDATE/DELETE
    """

    returning = None
    """holds the "returning" collection of columns if
    the statement is CRUD and defines returning columns
    either implicitly or explicitly
    """

    returning_precedes_values = False
    """set to True classwide to generate RETURNING
    clauses before the VALUES or WHERE clause (i.e. MSSQL)
    """

    render_table_with_column_in_update_from = False
    """set to True classwide to indicate the SET clause
    in a multi-table UPDATE statement should qualify
    columns with the table name (i.e. MySQL only)
    """

    ansi_bind_rules = False
    """SQL 92 doesn't allow bind parameters to be used
    in the columns clause of a SELECT, nor does it allow
    ambiguous expressions like "? = ?".  A compiler
    subclass can set this flag to False if the target
    driver/DB enforces this
    """

    def __init__(self, dialect, statement, column_keys=None, 
                    inline=False, **kwargs):
        """Construct a new ``DefaultCompiler`` object.

        dialect
          Dialect to be used

        statement
          ClauseElement to be compiled

        column_keys
          a list of column names to be compiled into an INSERT or UPDATE
          statement.

        """
        self.column_keys = column_keys

        # compile INSERT/UPDATE defaults/sequences inlined (no pre-
        # execute)
        self.inline = inline or getattr(statement, 'inline', False)

        # a dictionary of bind parameter keys to _BindParamClause
        # instances.
        self.binds = {}

        # a dictionary of _BindParamClause instances to "compiled" names
        # that are actually present in the generated SQL
        self.bind_names = util.column_dict()

        # stack which keeps track of nested SELECT statements
        self.stack = []

        # relates label names in the final SQL to a tuple of local
        # column/label name, ColumnElement object (if any) and
        # TypeEngine. ResultProxy uses this for type processing and
        # column targeting
        self.result_map = {}

        # collect CTEs to tack on top of a SELECT
        self.ctes = util.OrderedDict()
        self.ctes_recursive = False

        # true if the paramstyle is positional
        self.positional = dialect.positional
        if self.positional:
            self.positiontup = []
        self.bindtemplate = BIND_TEMPLATES[dialect.paramstyle]

        # an IdentifierPreparer that formats the quoting of identifiers
        self.preparer = dialect.identifier_preparer
        self.label_length = dialect.label_length \
            or dialect.max_identifier_length

        # a map which tracks "anonymous" identifiers that are created on
        # the fly here
        self.anon_map = util.PopulateDict(self._process_anon)

        # a map which tracks "truncated" names based on
        # dialect.label_length or dialect.max_identifier_length
        self.truncated_names = {}
        engine.Compiled.__init__(self, dialect, statement, **kwargs)



    @util.memoized_property
    def _bind_processors(self):
        return dict(
                (key, value) for key, value in
                ( (self.bind_names[bindparam],
                   bindparam.type._cached_bind_processor(self.dialect))
                  for bindparam in self.bind_names )
                 if value is not None
            )

    def is_subquery(self):
        return len(self.stack) > 1

    @property
    def sql_compiler(self):
        return self

    def construct_params(self, params=None, _group_number=None, _check=True):
        """return a dictionary of bind parameter keys and values"""

        if params:
            pd = {}
            for bindparam, name in self.bind_names.iteritems():
                if bindparam.key in params:
                    pd[name] = params[bindparam.key]
                elif name in params:
                    pd[name] = params[name]
                elif _check and bindparam.required:
                    if _group_number:
                        raise exc.InvalidRequestError(
                            "A value is required for bind parameter %r, "
                            "in parameter group %d" % 
                            (bindparam.key, _group_number))
                    else:
                        raise exc.InvalidRequestError(
                            "A value is required for bind parameter %r" 
                            % bindparam.key)
                else:
                    pd[name] = bindparam.effective_value
            return pd
        else:
            pd = {}
            for bindparam in self.bind_names:
                if _check and bindparam.required:
                    if _group_number:
                        raise exc.InvalidRequestError(
                            "A value is required for bind parameter %r, "
                            "in parameter group %d" % 
                            (bindparam.key, _group_number))
                    else:
                        raise exc.InvalidRequestError(
                            "A value is required for bind parameter %r" 
                            % bindparam.key)
                pd[self.bind_names[bindparam]] = bindparam.effective_value
            return pd

    @property
    def params(self):
        """Return the bind param dictionary embedded into this 
        compiled object, for those values that are present."""
        return self.construct_params(_check=False)

    def default_from(self):
        """Called when a SELECT statement has no froms, and no FROM clause is
        to be appended.

        Gives Oracle a chance to tack on a ``FROM DUAL`` to the string output.

        """
        return ""

    def visit_grouping(self, grouping, asfrom=False, **kwargs):
        return "(" + grouping.element._compiler_dispatch(self, **kwargs) + ")"

    def visit_label(self, label, result_map=None, 
                            within_label_clause=False, 
                            within_columns_clause=False, **kw):
        # only render labels within the columns clause
        # or ORDER BY clause of a select.  dialect-specific compilers
        # can modify this behavior.
        if within_columns_clause and not within_label_clause:
            if isinstance(label.name, sql._truncated_label):
                labelname = self._truncated_identifier("colident", label.name)
            else:
                labelname = label.name

            if result_map is not None:
                result_map[labelname.lower()] = (
                        label.name, 
                        (label, label.element, labelname, ) + 
                            label._alt_names,
                        label.type)

            return label.element._compiler_dispatch(self, 
                                    within_columns_clause=True,
                                    within_label_clause=True, 
                                    **kw) + \
                        OPERATORS[operators.as_] + \
                        self.preparer.format_label(label, labelname)
        else:
            return label.element._compiler_dispatch(self, 
                                    within_columns_clause=False, 
                                    **kw)

    def visit_column(self, column, result_map=None, **kwargs):
        name = orig_name = column.name
        if name is None:
            raise exc.CompileError("Cannot compile Column object until "
                                   "it's 'name' is assigned.")

        is_literal = column.is_literal
        if not is_literal and isinstance(name, sql._truncated_label):
            name = self._truncated_identifier("colident", name)

        if result_map is not None:
            result_map[name.lower()] = (orig_name, 
                                        (column, name, column.key), 
                                        column.type)

        if is_literal:
            name = self.escape_literal_column(name)
        else:
            name = self.preparer.quote(name, column.quote)

        table = column.table
        if table is None or not table.named_with_column:
            return name
        else:
            if table.schema:
                schema_prefix = self.preparer.quote_schema(
                                    table.schema, 
                                    table.quote_schema) + '.'
            else:
                schema_prefix = ''
            tablename = table.name
            if isinstance(tablename, sql._truncated_label):
                tablename = self._truncated_identifier("alias", tablename)

            return schema_prefix + \
                    self.preparer.quote(tablename, table.quote) + \
                    "." + name

    def escape_literal_column(self, text):
        """provide escaping for the literal_column() construct."""

        # TODO: some dialects might need different behavior here
        return text.replace('%', '%%')

    def visit_fromclause(self, fromclause, **kwargs):
        return fromclause.name

    def visit_index(self, index, **kwargs):
        return index.name

    def visit_typeclause(self, typeclause, **kwargs):
        return self.dialect.type_compiler.process(typeclause.type)

    def post_process_text(self, text):
        return text

    def visit_textclause(self, textclause, **kwargs):
        if textclause.typemap is not None:
            for colname, type_ in textclause.typemap.iteritems():
                self.result_map[colname.lower()] = (colname, None, type_)

        def do_bindparam(m):
            name = m.group(1)
            if name in textclause.bindparams:
                return self.process(textclause.bindparams[name])
            else:
                return self.bindparam_string(name)

        # un-escape any \:params
        return BIND_PARAMS_ESC.sub(lambda m: m.group(1),
            BIND_PARAMS.sub(do_bindparam,
             self.post_process_text(textclause.text))
        )

    def visit_null(self, expr, **kw):
        return 'NULL'

    def visit_true(self, expr, **kw):
        return 'true'

    def visit_false(self, expr, **kw):
        return 'false'

    def visit_clauselist(self, clauselist, **kwargs):
        sep = clauselist.operator
        if sep is None:
            sep = " "
        else:
            sep = OPERATORS[clauselist.operator]
        return sep.join(
                    s for s in 
                    (c._compiler_dispatch(self, **kwargs) 
                    for c in clauselist.clauses)
                    if s)

    def visit_case(self, clause, **kwargs):
        x = "CASE "
        if clause.value is not None:
            x += clause.value._compiler_dispatch(self, **kwargs) + " "
        for cond, result in clause.whens:
            x += "WHEN " + cond._compiler_dispatch(
                            self, **kwargs
                            ) + " THEN " + result._compiler_dispatch(
                                            self, **kwargs) + " "
        if clause.else_ is not None:
            x += "ELSE " + clause.else_._compiler_dispatch(
                                self, **kwargs
                            ) + " "
        x += "END"
        return x

    def visit_cast(self, cast, **kwargs):
        return "CAST(%s AS %s)" % \
                    (cast.clause._compiler_dispatch(self, **kwargs),
                    cast.typeclause._compiler_dispatch(self, **kwargs))

    def visit_over(self, over, **kwargs):
        x ="%s OVER (" % over.func._compiler_dispatch(self, **kwargs)
        if over.partition_by is not None:
            x += "PARTITION BY %s" % \
                over.partition_by._compiler_dispatch(self, **kwargs)
            if over.order_by is not None:
                x += " "
        if over.order_by is not None:
            x += "ORDER BY %s" % \
                over.order_by._compiler_dispatch(self, **kwargs)
        x += ")"
        return x

    def visit_extract(self, extract, **kwargs):
        field = self.extract_map.get(extract.field, extract.field)
        return "EXTRACT(%s FROM %s)" % (field, 
                            extract.expr._compiler_dispatch(self, **kwargs))

    def visit_function(self, func, result_map=None, **kwargs):
        if result_map is not None:
            result_map[func.name.lower()] = (func.name, None, func.type)

        disp = getattr(self, "visit_%s_func" % func.name.lower(), None)
        if disp:
            return disp(func, **kwargs)
        else:
            name = FUNCTIONS.get(func.__class__, func.name + "%(expr)s")
            return ".".join(list(func.packagenames) + [name]) % \
                            {'expr':self.function_argspec(func, **kwargs)}

    def visit_next_value_func(self, next_value, **kw):
        return self.visit_sequence(next_value.sequence)

    def visit_sequence(self, sequence):
        raise NotImplementedError(
            "Dialect '%s' does not support sequence increments." % self.dialect.name
        )

    def function_argspec(self, func, **kwargs):
        return func.clause_expr._compiler_dispatch(self, **kwargs)

    def visit_compound_select(self, cs, asfrom=False, 
                            parens=True, compound_index=1, **kwargs):
        entry = self.stack and self.stack[-1] or {}
        self.stack.append({'from':entry.get('from', None), 'iswrapper':True})

        keyword = self.compound_keywords.get(cs.keyword)

        text = (" " + keyword + " ").join(
                            (c._compiler_dispatch(self, 
                                            asfrom=asfrom, parens=False, 
                                            compound_index=i, **kwargs)
                            for i, c in enumerate(cs.selects))
                        )

        group_by = cs._group_by_clause._compiler_dispatch(
                                self, asfrom=asfrom, **kwargs)
        if group_by:
            text += " GROUP BY " + group_by

        text += self.order_by_clause(cs, **kwargs)
        text += (cs._limit is not None or cs._offset is not None) and \
                        self.limit_clause(cs) or ""

        self.stack.pop(-1)
        if asfrom and parens:
            return "(" + text + ")"
        else:
            return text

    def visit_unary(self, unary, **kw):
        s = unary.element._compiler_dispatch(self, **kw)
        if unary.operator:
            s = OPERATORS[unary.operator] + s
        if unary.modifier:
            s = s + OPERATORS[unary.modifier]
        return s

    def visit_binary(self, binary, **kw):
        # don't allow "? = ?" to render
        if self.ansi_bind_rules and \
            isinstance(binary.left, sql._BindParamClause) and \
            isinstance(binary.right, sql._BindParamClause):
            kw['literal_binds'] = True

        return self._operator_dispatch(binary.operator,
                    binary,
                    lambda opstr: binary.left._compiler_dispatch(self, **kw) + 
                                        opstr + 
                                    binary.right._compiler_dispatch(
                                            self, **kw),
                    **kw
        )

    def visit_like_op(self, binary, **kw):
        escape = binary.modifiers.get("escape", None)
        return '%s LIKE %s' % (
                            binary.left._compiler_dispatch(self, **kw), 
                            binary.right._compiler_dispatch(self, **kw)) \
            + (escape and 
                    (' ESCAPE ' + self.render_literal_value(escape, None))
                    or '')

    def visit_notlike_op(self, binary, **kw):
        escape = binary.modifiers.get("escape", None)
        return '%s NOT LIKE %s' % (
                            binary.left._compiler_dispatch(self, **kw), 
                            binary.right._compiler_dispatch(self, **kw)) \
            + (escape and 
                    (' ESCAPE ' + self.render_literal_value(escape, None))
                    or '')

    def visit_ilike_op(self, binary, **kw):
        escape = binary.modifiers.get("escape", None)
        return 'lower(%s) LIKE lower(%s)' % (
                            binary.left._compiler_dispatch(self, **kw), 
                            binary.right._compiler_dispatch(self, **kw)) \
            + (escape and 
                    (' ESCAPE ' + self.render_literal_value(escape, None))
                    or '')

    def visit_notilike_op(self, binary, **kw):
        escape = binary.modifiers.get("escape", None)
        return 'lower(%s) NOT LIKE lower(%s)' % (
                            binary.left._compiler_dispatch(self, **kw), 
                            binary.right._compiler_dispatch(self, **kw)) \
            + (escape and 
                    (' ESCAPE ' + self.render_literal_value(escape, None))
                    or '')

    def _operator_dispatch(self, operator, element, fn, **kw):
        if util.callable(operator):
            disp = getattr(self, "visit_%s" % operator.__name__, None)
            if disp:
                return disp(element, **kw)
            else:
                return fn(OPERATORS[operator])
        else:
            return fn(" " + operator + " ")

    def visit_bindparam(self, bindparam, within_columns_clause=False,
                                            literal_binds=False, **kwargs):

        if literal_binds or \
            (within_columns_clause and \
                self.ansi_bind_rules):
            if bindparam.value is None:
                raise exc.CompileError("Bind parameter without a "
                                        "renderable value not allowed here.")
            return self.render_literal_bindparam(bindparam,
                            within_columns_clause=True, **kwargs)

        name = self._truncate_bindparam(bindparam)

        if name in self.binds:
            existing = self.binds[name]
            if existing is not bindparam:
                if (existing.unique or bindparam.unique) and \
                    not existing.proxy_set.intersection(bindparam.proxy_set):
                    raise exc.CompileError(
                            "Bind parameter '%s' conflicts with "
                            "unique bind parameter of the same name" %
                            bindparam.key
                        )
                elif getattr(existing, '_is_crud', False) or \
                    getattr(bindparam, '_is_crud', False):
                    raise exc.CompileError(
                        "bindparam() name '%s' is reserved "
                        "for automatic usage in the VALUES or SET "
                        "clause of this "
                        "insert/update statement.   Please use a " 
                        "name other than column name when using bindparam() "
                        "with insert() or update() (for example, 'b_%s')."
                        % (bindparam.key, bindparam.key)
                    )

        self.binds[bindparam.key] = self.binds[name] = bindparam

        return self.bindparam_string(name)

    def render_literal_bindparam(self, bindparam, **kw):
        value = bindparam.value
        processor = bindparam.type._cached_bind_processor(self.dialect)
        if processor:
            value = processor(value)
        return self.render_literal_value(value, bindparam.type)

    def render_literal_value(self, value, type_):
        """Render the value of a bind parameter as a quoted literal.

        This is used for statement sections that do not accept bind parameters
        on the target driver/database.

        This should be implemented by subclasses using the quoting services
        of the DBAPI.

        """
        if isinstance(value, basestring):
            value = value.replace("'", "''")
            return "'%s'" % value
        elif value is None:
            return "NULL"
        elif isinstance(value, (float, int, long)):
            return repr(value)
        elif isinstance(value, decimal.Decimal):
            return str(value)
        else:
            raise NotImplementedError(
                        "Don't know how to literal-quote value %r" % value)

    def _truncate_bindparam(self, bindparam):
        if bindparam in self.bind_names:
            return self.bind_names[bindparam]

        bind_name = bindparam.key
        if isinstance(bind_name, sql._truncated_label):
            bind_name = self._truncated_identifier("bindparam", bind_name)

        # add to bind_names for translation
        self.bind_names[bindparam] = bind_name

        return bind_name

    def _truncated_identifier(self, ident_class, name):
        if (ident_class, name) in self.truncated_names:
            return self.truncated_names[(ident_class, name)]

        anonname = name.apply_map(self.anon_map)

        if len(anonname) > self.label_length:
            counter = self.truncated_names.get(ident_class, 1)
            truncname = anonname[0:max(self.label_length - 6, 0)] + \
                                "_" + hex(counter)[2:]
            self.truncated_names[ident_class] = counter + 1
        else:
            truncname = anonname
        self.truncated_names[(ident_class, name)] = truncname
        return truncname

    def _anonymize(self, name):
        return name % self.anon_map

    def _process_anon(self, key):
        (ident, derived) = key.split(' ', 1)
        anonymous_counter = self.anon_map.get(derived, 1)
        self.anon_map[derived] = anonymous_counter + 1
        return derived + "_" + str(anonymous_counter)

    def bindparam_string(self, name):
        if self.positional:
            self.positiontup.append(name)
            return self.bindtemplate % {
                        'name':name, 'position':len(self.positiontup)}
        else:
            return self.bindtemplate % {'name':name}

    def visit_cte(self, cte, asfrom=False, ashint=False, 
                                fromhints=None, **kwargs):
        if isinstance(cte.name, sql._truncated_label):
            cte_name = self._truncated_identifier("alias", cte.name)
        else:
            cte_name = cte.name
        if cte.cte_alias:
            if isinstance(cte.cte_alias, sql._truncated_label):
                cte_alias = self._truncated_identifier("alias", cte.cte_alias)
            else:
                cte_alias = cte.cte_alias
        if not cte.cte_alias and cte not in self.ctes:
            if cte.recursive:
                self.ctes_recursive = True
            text = self.preparer.format_alias(cte, cte_name)
            if cte.recursive:
                if isinstance(cte.original, sql.Select):
                    col_source = cte.original
                elif isinstance(cte.original, sql.CompoundSelect):
                    col_source = cte.original.selects[0]
                else:
                    assert False
                recur_cols = [c.key for c in util.unique_list(col_source.inner_columns)
                                if c is not None]

                text += "(%s)" % (", ".join(recur_cols))
            text += " AS \n" + \
                        cte.original._compiler_dispatch(
                                self, asfrom=True, **kwargs
                            )
            self.ctes[cte] = text
        if asfrom:
            if cte.cte_alias:
                text = self.preparer.format_alias(cte, cte_alias)
                text += " AS " + cte_name
            else:
                return self.preparer.format_alias(cte, cte_name)
            return text

    def visit_alias(self, alias, asfrom=False, ashint=False, 
                                fromhints=None, **kwargs):
        if asfrom or ashint:
            if isinstance(alias.name, sql._truncated_label):
                alias_name = self._truncated_identifier("alias", alias.name)
            else:
                alias_name = alias.name

        if ashint:
            return self.preparer.format_alias(alias, alias_name)
        elif asfrom:
            ret = alias.original._compiler_dispatch(self, 
                                asfrom=True, **kwargs) + \
                                " AS " + \
                    self.preparer.format_alias(alias, alias_name)

            if fromhints and alias in fromhints:
                hinttext = self.get_from_hint_text(alias, fromhints[alias])
                if hinttext:
                    ret += " " + hinttext

            return ret
        else:
            return alias.original._compiler_dispatch(self, **kwargs)

    def label_select_column(self, select, column, asfrom):
        """label columns present in a select()."""

        if isinstance(column, sql._Label):
            return column

        elif select is not None and \
                select.use_labels and \
                column._label:
            return _CompileLabel(
                    column, 
                    column._label, 
                    alt_names=(column._key_label, )
                )

        elif \
            asfrom and \
            isinstance(column, sql.ColumnClause) and \
            not column.is_literal and \
            column.table is not None and \
            not isinstance(column.table, sql.Select):
            return _CompileLabel(column, sql._as_truncated(column.name), 
                                        alt_names=(column.key,))
        elif not isinstance(column, 
                    (sql._UnaryExpression, sql._TextClause)) \
                and (not hasattr(column, 'name') or \
                        isinstance(column, sql.Function)):
            return _CompileLabel(column, column.anon_label)
        else:
            return column

    def get_select_hint_text(self, byfroms):
        return None

    def get_from_hint_text(self, table, text):
        return None

    def get_crud_hint_text(self, table, text):
        return None

    def visit_select(self, select, asfrom=False, parens=True, 
                            iswrapper=False, fromhints=None, 
                            compound_index=1, **kwargs):

        entry = self.stack and self.stack[-1] or {}

        existingfroms = entry.get('from', None)

        froms = select._get_display_froms(existingfroms)

        correlate_froms = set(sql._from_objects(*froms))

        # TODO: might want to propagate existing froms for
        # select(select(select)) where innermost select should correlate
        # to outermost if existingfroms: correlate_froms =
        # correlate_froms.union(existingfroms)

        self.stack.append({'from': correlate_froms, 'iswrapper'
                          : iswrapper})

        if compound_index==1 and not entry or entry.get('iswrapper', False):
            column_clause_args = {'result_map':self.result_map}
        else:
            column_clause_args = {}

        # the actual list of columns to print in the SELECT column list.
        inner_columns = [
            c for c in [
                self.label_select_column(select, co, asfrom=asfrom).\
                    _compiler_dispatch(self,
                        within_columns_clause=True,
                        **column_clause_args) 
                for co in util.unique_list(select.inner_columns)
            ]
            if c is not None
        ]

        text = "SELECT "  # we're off to a good start !

        if select._hints:
            byfrom = dict([
                            (from_, hinttext % {
                                'name':from_._compiler_dispatch(
                                    self, ashint=True)
                            }) 
                            for (from_, dialect), hinttext in 
                            select._hints.iteritems() 
                            if dialect in ('*', self.dialect.name)
                        ])
            hint_text = self.get_select_hint_text(byfrom)
            if hint_text:
                text += hint_text + " "

        if select._prefixes:
            text += " ".join(
                            x._compiler_dispatch(self, **kwargs) 
                            for x in select._prefixes) + " "
        text += self.get_select_precolumns(select)
        text += ', '.join(inner_columns)

        if froms:
            text += " \nFROM "

            if select._hints:
                text += ', '.join([f._compiler_dispatch(self, 
                                    asfrom=True, fromhints=byfrom, 
                                    **kwargs) 
                                for f in froms])
            else:
                text += ', '.join([f._compiler_dispatch(self, 
                                    asfrom=True, **kwargs) 
                                for f in froms])
        else:
            text += self.default_from()

        if select._whereclause is not None:
            t = select._whereclause._compiler_dispatch(self, **kwargs)
            if t:
                text += " \nWHERE " + t

        if select._group_by_clause.clauses:
            group_by = select._group_by_clause._compiler_dispatch(
                                        self, **kwargs)
            if group_by:
                text += " GROUP BY " + group_by

        if select._having is not None:
            t = select._having._compiler_dispatch(self, **kwargs)
            if t:
                text += " \nHAVING " + t

        if select._order_by_clause.clauses:
            text += self.order_by_clause(select, **kwargs)
        if select._limit is not None or select._offset is not None:
            text += self.limit_clause(select)
        if select.for_update:
            text += self.for_update_clause(select)

        if self.ctes and \
            compound_index==1 and not entry:
            cte_text = self.get_cte_preamble(self.ctes_recursive) + " "
            cte_text += ", \n".join(
                [txt for txt in self.ctes.values()]
            )
            cte_text += "\n "
            text = cte_text + text

        self.stack.pop(-1)

        if asfrom and parens:
            return "(" + text + ")"
        else:
            return text

    def get_cte_preamble(self, recursive):
        if recursive:
            return "WITH RECURSIVE"
        else:
            return "WITH"

    def get_select_precolumns(self, select):
        """Called when building a ``SELECT`` statement, position is just
        before column list.

        """
        return select._distinct and "DISTINCT " or ""

    def order_by_clause(self, select, **kw):
        order_by = select._order_by_clause._compiler_dispatch(self, **kw)
        if order_by:
            return " ORDER BY " + order_by
        else:
            return ""

    def for_update_clause(self, select):
        if select.for_update:
            return " FOR UPDATE"
        else:
            return ""

    def limit_clause(self, select):
        text = ""
        if select._limit is not None:
            text +=  "\n LIMIT " + self.process(sql.literal(select._limit))
        if select._offset is not None:
            if select._limit is None:
                text += "\n LIMIT -1"
            text += " OFFSET " + self.process(sql.literal(select._offset))
        return text

    def visit_table(self, table, asfrom=False, ashint=False, 
                        fromhints=None, **kwargs):
        if asfrom or ashint:
            if getattr(table, "schema", None):
                ret = self.preparer.quote_schema(table.schema,
                                table.quote_schema) + \
                                "." + self.preparer.quote(table.name,
                                                table.quote)
            else:
                ret = self.preparer.quote(table.name, table.quote)
            if fromhints and table in fromhints:
                hinttext = self.get_from_hint_text(table, fromhints[table])
                if hinttext:
                    ret += " " + hinttext
            return ret
        else:
            return ""

    def visit_join(self, join, asfrom=False, **kwargs):
        return (
            join.left._compiler_dispatch(self, asfrom=True, **kwargs) + 
            (join.isouter and " LEFT OUTER JOIN " or " JOIN ") + 
            join.right._compiler_dispatch(self, asfrom=True, **kwargs) + 
            " ON " + 
            join.onclause._compiler_dispatch(self, **kwargs)
        )

    def visit_insert(self, insert_stmt):
        self.isinsert = True
        colparams = self._get_colparams(insert_stmt)

        if not colparams and \
                not self.dialect.supports_default_values and \
                not self.dialect.supports_empty_insert:
            raise exc.CompileError("The version of %s you are using does "
                                    "not support empty inserts." % 
                                    self.dialect.name)

        preparer = self.preparer
        supports_default_values = self.dialect.supports_default_values

        text = "INSERT"


        prefixes = [self.process(x) for x in insert_stmt._prefixes]
        if prefixes:
            text += " " + " ".join(prefixes)

        text += " INTO " + preparer.format_table(insert_stmt.table)

        if insert_stmt._hints:
            dialect_hints = dict([
                (table, hint_text)
                for (table, dialect), hint_text in 
                insert_stmt._hints.items()
                if dialect in ('*', self.dialect.name)
            ])
            if insert_stmt.table in dialect_hints:
                text += " " + self.get_crud_hint_text(
                                    insert_stmt.table, 
                                    dialect_hints[insert_stmt.table]
                                )

        if colparams or not supports_default_values:
            text += " (%s)" % ', '.join([preparer.format_column(c[0])
                       for c in colparams])

        if self.returning or insert_stmt._returning:
            self.returning = self.returning or insert_stmt._returning
            returning_clause = self.returning_clause(
                                    insert_stmt, self.returning)

            if self.returning_precedes_values:
                text += " " + returning_clause

        if not colparams and supports_default_values:
            text += " DEFAULT VALUES"
        else:
            text += " VALUES (%s)" % \
                     ', '.join([c[1] for c in colparams])

        if self.returning and not self.returning_precedes_values:
            text += " " + returning_clause

        return text

    def update_limit_clause(self, update_stmt):
        """Provide a hook for MySQL to add LIMIT to the UPDATE"""
        return None

    def update_tables_clause(self, update_stmt, from_table, 
                                            extra_froms, **kw):
        """Provide a hook to override the initial table clause
        in an UPDATE statement.

        MySQL overrides this.

        """
        return self.preparer.format_table(from_table)

    def update_from_clause(self, update_stmt, 
                                from_table, extra_froms, 
                                from_hints,
                                **kw):
        """Provide a hook to override the generation of an 
        UPDATE..FROM clause.

        MySQL and MSSQL override this.

        """
        return "FROM " + ', '.join(
                    t._compiler_dispatch(self, asfrom=True, 
                                    fromhints=from_hints, **kw) 
                    for t in extra_froms)

    def visit_update(self, update_stmt, **kw):
        self.stack.append({'from': set([update_stmt.table])})

        self.isupdate = True

        extra_froms = update_stmt._extra_froms

        colparams = self._get_colparams(update_stmt, extra_froms)

        text = "UPDATE " + self.update_tables_clause(
                                        update_stmt, 
                                        update_stmt.table, 
                                        extra_froms, **kw)

        if update_stmt._hints:
            dialect_hints = dict([
                (table, hint_text)
                for (table, dialect), hint_text in 
                update_stmt._hints.items()
                if dialect in ('*', self.dialect.name)
            ])
            if update_stmt.table in dialect_hints:
                text += " " + self.get_crud_hint_text(
                                    update_stmt.table, 
                                    dialect_hints[update_stmt.table]
                                )
        else:
            dialect_hints = None

        text += ' SET '
        if extra_froms and self.render_table_with_column_in_update_from:
            text += ', '.join(
                            self.visit_column(c[0]) + 
                            '=' + c[1] for c in colparams
                            )
        else:
            text += ', '.join(
                        self.preparer.quote(c[0].name, c[0].quote) + 
                        '=' + c[1] for c in colparams
                            )

        if update_stmt._returning:
            self.returning = update_stmt._returning
            if self.returning_precedes_values:
                text += " " + self.returning_clause(
                                    update_stmt, update_stmt._returning)

        if extra_froms:
            extra_from_text = self.update_from_clause(
                                        update_stmt, 
                                        update_stmt.table, 
                                        extra_froms, 
                                        dialect_hints, **kw)
            if extra_from_text:
                text += " " + extra_from_text

        if update_stmt._whereclause is not None:
            text += " WHERE " + self.process(update_stmt._whereclause)

        limit_clause = self.update_limit_clause(update_stmt)
        if limit_clause:
            text += " " + limit_clause

        if self.returning and not self.returning_precedes_values:
            text += " " + self.returning_clause(
                                    update_stmt, update_stmt._returning)

        self.stack.pop(-1)

        return text

    def _create_crud_bind_param(self, col, value, required=False):
        bindparam = sql.bindparam(col.key, value, 
                            type_=col.type, required=required)
        bindparam._is_crud = True
        return bindparam._compiler_dispatch(self)


    def _get_colparams(self, stmt, extra_tables=None):
        """create a set of tuples representing column/string pairs for use
        in an INSERT or UPDATE statement.

        Also generates the Compiled object's postfetch, prefetch, and
        returning column collections, used for default handling and ultimately
        populating the ResultProxy's prefetch_cols() and postfetch_cols()
        collections.

        """

        self.postfetch = []
        self.prefetch = []
        self.returning = []

        # no parameters in the statement, no parameters in the
        # compiled params - return binds for all columns
        if self.column_keys is None and stmt.parameters is None:
            return [
                        (c, self._create_crud_bind_param(c, 
                                    None, required=True)) 
                        for c in stmt.table.columns
                    ]

        required = object()

        # if we have statement parameters - set defaults in the
        # compiled params
        if self.column_keys is None:
            parameters = {}
        else:
            parameters = dict((sql._column_as_key(key), required)
                              for key in self.column_keys 
                              if not stmt.parameters or 
                              key not in stmt.parameters)

        if stmt.parameters is not None:
            for k, v in stmt.parameters.iteritems():
                parameters.setdefault(sql._column_as_key(k), v)

        # create a list of column assignment clauses as tuples
        values = []

        need_pks = self.isinsert and \
                        not self.inline and \
                        not stmt._returning

        implicit_returning = need_pks and \
                                self.dialect.implicit_returning and \
                                stmt.table.implicit_returning

        postfetch_lastrowid = need_pks and self.dialect.postfetch_lastrowid

        check_columns = {}
        # special logic that only occurs for multi-table UPDATE 
        # statements
        if extra_tables and stmt.parameters:
            assert self.isupdate
            affected_tables = set()
            for t in extra_tables:
                for c in t.c:
                    if c in stmt.parameters:
                        affected_tables.add(t)
                        check_columns[c.key] = c
                        value = stmt.parameters[c]
                        if sql._is_literal(value):
                            value = self._create_crud_bind_param(
                                            c, value, required=value is required)
                        else:
                            self.postfetch.append(c)
                            value = self.process(value.self_group())
                        values.append((c, value))
            # determine tables which are actually
            # to be updated - process onupdate and 
            # server_onupdate for these
            for t in affected_tables:
                for c in t.c:
                    if c in stmt.parameters:
                        continue
                    elif c.onupdate is not None and not c.onupdate.is_sequence:
                        if c.onupdate.is_clause_element:
                            values.append(
                                (c, self.process(c.onupdate.arg.self_group()))
                            )
                            self.postfetch.append(c)
                        else:
                            values.append(
                                (c, self._create_crud_bind_param(c, None))
                            )
                            self.prefetch.append(c)
                    elif c.server_onupdate is not None:
                        self.postfetch.append(c)

        # iterating through columns at the top to maintain ordering.
        # otherwise we might iterate through individual sets of 
        # "defaults", "primary key cols", etc.
        for c in stmt.table.columns:
            if c.key in parameters and c.key not in check_columns:
                value = parameters.pop(c.key)
                if sql._is_literal(value):
                    value = self._create_crud_bind_param(
                                    c, value, required=value is required)
                elif c.primary_key and implicit_returning:
                    self.returning.append(c)
                    value = self.process(value.self_group())
                else:
                    self.postfetch.append(c)
                    value = self.process(value.self_group())
                values.append((c, value))

            elif self.isinsert:
                if c.primary_key and \
                    need_pks and \
                    (
                        implicit_returning or 
                        not postfetch_lastrowid or 
                        c is not stmt.table._autoincrement_column
                    ):

                    if implicit_returning:
                        if c.default is not None:
                            if c.default.is_sequence:
                                if self.dialect.supports_sequences and \
                                    (not c.default.optional or \
                                    not self.dialect.sequences_optional):
                                    proc = self.process(c.default)
                                    values.append((c, proc))
                                self.returning.append(c)
                            elif c.default.is_clause_element:
                                values.append(
                                    (c,
                                    self.process(c.default.arg.self_group()))
                                )
                                self.returning.append(c)
                            else:
                                values.append(
                                    (c, self._create_crud_bind_param(c, None))
                                )
                                self.prefetch.append(c)
                        else:
                            self.returning.append(c)
                    else:
                        if c.default is not None or \
                            c is stmt.table._autoincrement_column and (
                                self.dialect.supports_sequences or
                                self.dialect.preexecute_autoincrement_sequences
                            ):

                            values.append(
                                (c, self._create_crud_bind_param(c, None))
                            )

                            self.prefetch.append(c)

                elif c.default is not None:
                    if c.default.is_sequence:
                        if self.dialect.supports_sequences and \
                            (not c.default.optional or \
                            not self.dialect.sequences_optional):
                            proc = self.process(c.default)
                            values.append((c, proc))
                            if not c.primary_key:
                                self.postfetch.append(c)
                    elif c.default.is_clause_element:
                        values.append(
                            (c, self.process(c.default.arg.self_group()))
                        )

                        if not c.primary_key:
                            # dont add primary key column to postfetch
                            self.postfetch.append(c)
                    else:
                        values.append(
                            (c, self._create_crud_bind_param(c, None))
                        )
                        self.prefetch.append(c)
                elif c.server_default is not None:
                    if not c.primary_key:
                        self.postfetch.append(c)

            elif self.isupdate:
                if c.onupdate is not None and not c.onupdate.is_sequence:
                    if c.onupdate.is_clause_element:
                        values.append(
                            (c, self.process(c.onupdate.arg.self_group()))
                        )
                        self.postfetch.append(c)
                    else:
                        values.append(
                            (c, self._create_crud_bind_param(c, None))
                        )
                        self.prefetch.append(c)
                elif c.server_onupdate is not None:
                    self.postfetch.append(c)

        if parameters and stmt.parameters:
            check = set(parameters).intersection(
                sql._column_as_key(k) for k in stmt.parameters
            ).difference(check_columns)
            if check:
                util.warn(
                    "Unconsumed column names: %s" % 
                    (", ".join(check))
                )

        return values

    def visit_delete(self, delete_stmt):
        self.stack.append({'from': set([delete_stmt.table])})
        self.isdelete = True

        text = "DELETE FROM " + self.preparer.format_table(delete_stmt.table)

        if delete_stmt._hints:
            dialect_hints = dict([
                (table, hint_text)
                for (table, dialect), hint_text in 
                delete_stmt._hints.items()
                if dialect in ('*', self.dialect.name)
            ])
            if delete_stmt.table in dialect_hints:
                text += " " + self.get_crud_hint_text(
                                    delete_stmt.table, 
                                    dialect_hints[delete_stmt.table]
                                )
        else:
            dialect_hints = None

        if delete_stmt._returning:
            self.returning = delete_stmt._returning
            if self.returning_precedes_values:
                text += " " + self.returning_clause(
                                delete_stmt, delete_stmt._returning)

        if delete_stmt._whereclause is not None:
            text += " WHERE " + self.process(delete_stmt._whereclause)

        if self.returning and not self.returning_precedes_values:
            text += " " + self.returning_clause(
                                delete_stmt, delete_stmt._returning)

        self.stack.pop(-1)

        return text

    def visit_savepoint(self, savepoint_stmt):
        return "SAVEPOINT %s" % self.preparer.format_savepoint(savepoint_stmt)

    def visit_rollback_to_savepoint(self, savepoint_stmt):
        return "ROLLBACK TO SAVEPOINT %s" % \
                self.preparer.format_savepoint(savepoint_stmt)

    def visit_release_savepoint(self, savepoint_stmt):
        return "RELEASE SAVEPOINT %s" % \
                self.preparer.format_savepoint(savepoint_stmt)


class DDLCompiler(engine.Compiled):

    @util.memoized_property
    def sql_compiler(self):
        return self.dialect.statement_compiler(self.dialect, None)

    @property
    def preparer(self):
        return self.dialect.identifier_preparer

    def construct_params(self, params=None):
        return None

    def visit_ddl(self, ddl, **kwargs):
        # table events can substitute table and schema name
        context = ddl.context
        if isinstance(ddl.target, schema.Table):
            context = context.copy()

            preparer = self.dialect.identifier_preparer
            path = preparer.format_table_seq(ddl.target)
            if len(path) == 1:
                table, sch = path[0], ''
            else:
                table, sch = path[-1], path[0]

            context.setdefault('table', table)
            context.setdefault('schema', sch)
            context.setdefault('fullname', preparer.format_table(ddl.target))

        return self.sql_compiler.post_process_text(ddl.statement % context)

    def visit_create_schema(self, create):
        return "CREATE SCHEMA " + self.preparer.format_schema(create.element, create.quote)

    def visit_drop_schema(self, drop):
        text = "DROP SCHEMA " + self.preparer.format_schema(drop.element, drop.quote)
        if drop.cascade:
            text += " CASCADE"
        return text

    def visit_create_table(self, create):
        table = create.element
        preparer = self.dialect.identifier_preparer

        text = "\n" + " ".join(['CREATE'] + \
                                    table._prefixes + \
                                    ['TABLE',
                                     preparer.format_table(table),
                                     "("])
        separator = "\n"

        # if only one primary key, specify it along with the column
        first_pk = False
        for column in table.columns:
            try:
                text += separator
                separator = ", \n"
                text += "\t" + self.get_column_specification(
                                                column, 
                                                first_pk=column.primary_key and \
                                                not first_pk
                                            )
                if column.primary_key:
                    first_pk = True
                const = " ".join(self.process(constraint) \
                                for constraint in column.constraints)
                if const:
                    text += " " + const
            except exc.CompileError, ce:
                # Py3K
                #raise exc.CompileError("(in table '%s', column '%s'): %s" 
                #                             % (
                #                                table.description, 
                #                                column.name, 
                #                                ce.args[0]
                #                            )) from ce
                # Py2K
                raise exc.CompileError("(in table '%s', column '%s'): %s" 
                                            % (
                                                table.description, 
                                                column.name,
                                                ce.args[0]
                                            )), None, sys.exc_info()[2]
                # end Py2K

        const = self.create_table_constraints(table)
        if const:
            text += ", \n\t" + const

        text += "\n)%s\n\n" % self.post_create_table(table)
        return text

    def create_table_constraints(self, table):

        # On some DB order is significant: visit PK first, then the
        # other constraints (engine.ReflectionTest.testbasic failed on FB2)
        constraints = []
        if table.primary_key:
            constraints.append(table.primary_key)

        constraints.extend([c for c in table._sorted_constraints 
                                if c is not table.primary_key])

        return ", \n\t".join(p for p in
                        (self.process(constraint) 
                        for constraint in constraints 
                        if (
                            constraint._create_rule is None or
                            constraint._create_rule(self))
                        and (
                            not self.dialect.supports_alter or 
                            not getattr(constraint, 'use_alter', False)
                        )) if p is not None
                )

    def visit_drop_table(self, drop):
        return "\nDROP TABLE " + self.preparer.format_table(drop.element)

    def _index_identifier(self, ident):
        if isinstance(ident, sql._truncated_label):
            max = self.dialect.max_index_name_length or \
                        self.dialect.max_identifier_length
            if len(ident) > max:
                return ident[0:max - 8] + \
                                "_" + util.md5_hex(ident)[-4:]
            else:
                return ident
        else:
            self.dialect.validate_identifier(ident)
            return ident

    def visit_create_index(self, create):
        index = create.element
        preparer = self.preparer
        text = "CREATE "
        if index.unique:
            text += "UNIQUE "
        text += "INDEX %s ON %s (%s)" \
                    % (preparer.quote(self._index_identifier(index.name), 
                        index.quote),
                       preparer.format_table(index.table),
                       ', '.join(preparer.quote(c.name, c.quote)
                                 for c in index.columns))
        return text

    def visit_drop_index(self, drop):
        index = drop.element
        return "\nDROP INDEX " + \
                    self.preparer.quote(
                            self._index_identifier(index.name), index.quote)

    def visit_add_constraint(self, create):
        preparer = self.preparer
        return "ALTER TABLE %s ADD %s" % (
            self.preparer.format_table(create.element.table),
            self.process(create.element)
        )

    def visit_create_sequence(self, create):
        text = "CREATE SEQUENCE %s" % \
                self.preparer.format_sequence(create.element)
        if create.element.increment is not None:
            text += " INCREMENT BY %d" % create.element.increment
        if create.element.start is not None:
            text += " START WITH %d" % create.element.start
        return text

    def visit_drop_sequence(self, drop):
        return "DROP SEQUENCE %s" % \
                self.preparer.format_sequence(drop.element)

    def visit_drop_constraint(self, drop):
        preparer = self.preparer
        return "ALTER TABLE %s DROP CONSTRAINT %s%s" % (
            self.preparer.format_table(drop.element.table),
            self.preparer.format_constraint(drop.element),
            drop.cascade and " CASCADE" or ""
        )

    def get_column_specification(self, column, **kwargs):
        colspec = self.preparer.format_column(column) + " " + \
                        self.dialect.type_compiler.process(column.type)
        default = self.get_column_default_string(column)
        if default is not None:
            colspec += " DEFAULT " + default

        if not column.nullable:
            colspec += " NOT NULL"
        return colspec

    def post_create_table(self, table):
        return ''

    def get_column_default_string(self, column):
        if isinstance(column.server_default, schema.DefaultClause):
            if isinstance(column.server_default.arg, basestring):
                return "'%s'" % column.server_default.arg
            else:
                return self.sql_compiler.process(column.server_default.arg)
        else:
            return None

    def visit_check_constraint(self, constraint):
        text = ""
        if constraint.name is not None:
            text += "CONSTRAINT %s " % \
                        self.preparer.format_constraint(constraint)
        sqltext = sql_util.expression_as_ddl(constraint.sqltext)
        text += "CHECK (%s)" % self.sql_compiler.process(sqltext)
        text += self.define_constraint_deferrability(constraint)
        return text

    def visit_column_check_constraint(self, constraint):
        text = ""
        if constraint.name is not None:
            text += "CONSTRAINT %s " % \
                        self.preparer.format_constraint(constraint)
        text += "CHECK (%s)" % constraint.sqltext
        text += self.define_constraint_deferrability(constraint)
        return text

    def visit_primary_key_constraint(self, constraint):
        if len(constraint) == 0:
            return ''
        text = ""
        if constraint.name is not None:
            text += "CONSTRAINT %s " % \
                    self.preparer.format_constraint(constraint)
        text += "PRIMARY KEY "
        text += "(%s)" % ', '.join(self.preparer.quote(c.name, c.quote)
                                       for c in constraint)
        text += self.define_constraint_deferrability(constraint)
        return text

    def visit_foreign_key_constraint(self, constraint):
        preparer = self.dialect.identifier_preparer
        text = ""
        if constraint.name is not None:
            text += "CONSTRAINT %s " % \
                        preparer.format_constraint(constraint)
        remote_table = list(constraint._elements.values())[0].column.table
        text += "FOREIGN KEY(%s) REFERENCES %s (%s)" % (
            ', '.join(preparer.quote(f.parent.name, f.parent.quote)
                      for f in constraint._elements.values()),
            self.define_constraint_remote_table(
                            constraint, remote_table, preparer),
            ', '.join(preparer.quote(f.column.name, f.column.quote)
                      for f in constraint._elements.values())
        )
        text += self.define_constraint_cascades(constraint)
        text += self.define_constraint_deferrability(constraint)
        return text

    def define_constraint_remote_table(self, constraint, table, preparer):
        """Format the remote table clause of a CREATE CONSTRAINT clause."""

        return preparer.format_table(table)

    def visit_unique_constraint(self, constraint):
        text = ""
        if constraint.name is not None:
            text += "CONSTRAINT %s " % \
                    self.preparer.format_constraint(constraint)
        text += "UNIQUE (%s)" % (
                    ', '.join(self.preparer.quote(c.name, c.quote) 
                            for c in constraint))
        text += self.define_constraint_deferrability(constraint)
        return text

    def define_constraint_cascades(self, constraint):
        text = ""
        if constraint.ondelete is not None:
            text += " ON DELETE %s" % constraint.ondelete
        if constraint.onupdate is not None:
            text += " ON UPDATE %s" % constraint.onupdate
        return text

    def define_constraint_deferrability(self, constraint):
        text = ""
        if constraint.deferrable is not None:
            if constraint.deferrable:
                text += " DEFERRABLE"
            else:
                text += " NOT DEFERRABLE"
        if constraint.initially is not None:
            text += " INITIALLY %s" % constraint.initially
        return text


class GenericTypeCompiler(engine.TypeCompiler):
    def visit_CHAR(self, type_):
        return "CHAR" + (type_.length and "(%d)" % type_.length or "")

    def visit_NCHAR(self, type_):
        return "NCHAR" + (type_.length and "(%d)" % type_.length or "")

    def visit_FLOAT(self, type_):
        return "FLOAT"

    def visit_REAL(self, type_):
        return "REAL"

    def visit_NUMERIC(self, type_):
        if type_.precision is None:
            return "NUMERIC"
        elif type_.scale is None:
            return "NUMERIC(%(precision)s)" % \
                        {'precision': type_.precision}
        else:
            return "NUMERIC(%(precision)s, %(scale)s)" % \
                        {'precision': type_.precision, 
                        'scale' : type_.scale}

    def visit_DECIMAL(self, type_):
        return "DECIMAL"

    def visit_INTEGER(self, type_):
        return "INTEGER"

    def visit_SMALLINT(self, type_):
        return "SMALLINT"

    def visit_BIGINT(self, type_):
        return "BIGINT"

    def visit_TIMESTAMP(self, type_):
        return 'TIMESTAMP'

    def visit_DATETIME(self, type_):
        return "DATETIME"

    def visit_DATE(self, type_):
        return "DATE"

    def visit_TIME(self, type_):
        return "TIME"

    def visit_CLOB(self, type_):
        return "CLOB"

    def visit_NCLOB(self, type_):
        return "NCLOB"

    def visit_VARCHAR(self, type_):
        return "VARCHAR" + (type_.length and "(%d)" % type_.length or "")

    def visit_NVARCHAR(self, type_):
        return "NVARCHAR" + (type_.length and "(%d)" % type_.length or "")

    def visit_BLOB(self, type_):
        return "BLOB"

    def visit_BINARY(self, type_):
        return "BINARY" + (type_.length and "(%d)" % type_.length or "")

    def visit_VARBINARY(self, type_):
        return "VARBINARY" + (type_.length and "(%d)" % type_.length or "")

    def visit_BOOLEAN(self, type_):
        return "BOOLEAN"

    def visit_TEXT(self, type_):
        return "TEXT"

    def visit_large_binary(self, type_):
        return self.visit_BLOB(type_)

    def visit_boolean(self, type_): 
        return self.visit_BOOLEAN(type_)

    def visit_time(self, type_): 
        return self.visit_TIME(type_)

    def visit_datetime(self, type_): 
        return self.visit_DATETIME(type_)

    def visit_date(self, type_): 
        return self.visit_DATE(type_)

    def visit_big_integer(self, type_): 
        return self.visit_BIGINT(type_)

    def visit_small_integer(self, type_): 
        return self.visit_SMALLINT(type_)

    def visit_integer(self, type_): 
        return self.visit_INTEGER(type_)

    def visit_real(self, type_):
        return self.visit_REAL(type_)

    def visit_float(self, type_):
        return self.visit_FLOAT(type_)

    def visit_numeric(self, type_): 
        return self.visit_NUMERIC(type_)

    def visit_string(self, type_): 
        return self.visit_VARCHAR(type_)

    def visit_unicode(self, type_): 
        return self.visit_VARCHAR(type_)

    def visit_text(self, type_): 
        return self.visit_TEXT(type_)

    def visit_unicode_text(self, type_): 
        return self.visit_TEXT(type_)

    def visit_enum(self, type_):
        return self.visit_VARCHAR(type_)

    def visit_null(self, type_):
        raise NotImplementedError("Can't generate DDL for the null type")

    def visit_type_decorator(self, type_):
        return self.process(type_.type_engine(self.dialect))

    def visit_user_defined(self, type_):
        return type_.get_col_spec()

class IdentifierPreparer(object):
    """Handle quoting and case-folding of identifiers based on options."""

    reserved_words = RESERVED_WORDS

    legal_characters = LEGAL_CHARACTERS

    illegal_initial_characters = ILLEGAL_INITIAL_CHARACTERS

    def __init__(self, dialect, initial_quote='"', 
                    final_quote=None, escape_quote='"', omit_schema=False):
        """Construct a new ``IdentifierPreparer`` object.

        initial_quote
          Character that begins a delimited identifier.

        final_quote
          Character that ends a delimited identifier. Defaults to
          `initial_quote`.

        omit_schema
          Prevent prepending schema name. Useful for databases that do
          not support schemae.
        """

        self.dialect = dialect
        self.initial_quote = initial_quote
        self.final_quote = final_quote or self.initial_quote
        self.escape_quote = escape_quote
        self.escape_to_quote = self.escape_quote * 2
        self.omit_schema = omit_schema
        self._strings = {}

    def _escape_identifier(self, value):
        """Escape an identifier.

        Subclasses should override this to provide database-dependent
        escaping behavior.
        """

        return value.replace(self.escape_quote, self.escape_to_quote)

    def _unescape_identifier(self, value):
        """Canonicalize an escaped identifier.

        Subclasses should override this to provide database-dependent
        unescaping behavior that reverses _escape_identifier.
        """

        return value.replace(self.escape_to_quote, self.escape_quote)

    def quote_identifier(self, value):
        """Quote an identifier.

        Subclasses should override this to provide database-dependent
        quoting behavior.
        """

        return self.initial_quote + \
                    self._escape_identifier(value) + \
                    self.final_quote

    def _requires_quotes(self, value):
        """Return True if the given identifier requires quoting."""
        lc_value = value.lower()
        return (lc_value in self.reserved_words
                or value[0] in self.illegal_initial_characters
                or not self.legal_characters.match(unicode(value))
                or (lc_value != value))

    def quote_schema(self, schema, force):
        """Quote a schema.

        Subclasses should override this to provide database-dependent 
        quoting behavior.
        """
        return self.quote(schema, force)

    def quote(self, ident, force):
        if force is None:
            if ident in self._strings:
                return self._strings[ident]
            else:
                if self._requires_quotes(ident):
                    self._strings[ident] = self.quote_identifier(ident)
                else:
                    self._strings[ident] = ident
                return self._strings[ident]
        elif force:
            return self.quote_identifier(ident)
        else:
            return ident

    def format_sequence(self, sequence, use_schema=True):
        name = self.quote(sequence.name, sequence.quote)
        if not self.omit_schema and use_schema and \
            sequence.schema is not None:
            name = self.quote_schema(sequence.schema, sequence.quote) + \
                        "." + name
        return name

    def format_label(self, label, name=None):
        return self.quote(name or label.name, label.quote)

    def format_alias(self, alias, name=None):
        return self.quote(name or alias.name, alias.quote)

    def format_savepoint(self, savepoint, name=None):
        return self.quote(name or savepoint.ident, savepoint.quote)

    def format_constraint(self, constraint):
        return self.quote(constraint.name, constraint.quote)

    def format_table(self, table, use_schema=True, name=None):
        """Prepare a quoted table and schema name."""

        if name is None:
            name = table.name
        result = self.quote(name, table.quote)
        if not self.omit_schema and use_schema \
            and getattr(table, "schema", None):
            result = self.quote_schema(table.schema, table.quote_schema) + \
                                "." + result
        return result

    def format_schema(self, name, quote):
        """Prepare a quoted schema name."""

        return self.quote(name, quote)

    def format_column(self, column, use_table=False, 
                            name=None, table_name=None):
        """Prepare a quoted column name."""

        if name is None:
            name = column.name
        if not getattr(column, 'is_literal', False):
            if use_table:
                return self.format_table(
                            column.table, use_schema=False, 
                            name=table_name) + "." + \
                            self.quote(name, column.quote)
            else:
                return self.quote(name, column.quote)
        else:
            # literal textual elements get stuck into ColumnClause a lot,
            # which shouldn't get quoted

            if use_table:
                return self.format_table(column.table,
                        use_schema=False, name=table_name) + '.' + name
            else:
                return name

    def format_table_seq(self, table, use_schema=True):
        """Format table name and schema as a tuple."""

        # Dialects with more levels in their fully qualified references
        # ('database', 'owner', etc.) could override this and return
        # a longer sequence.

        if not self.omit_schema and use_schema and \
                getattr(table, 'schema', None):
            return (self.quote_schema(table.schema, table.quote_schema),
                    self.format_table(table, use_schema=False))
        else:
            return (self.format_table(table, use_schema=False), )

    @util.memoized_property
    def _r_identifiers(self):
        initial, final, escaped_final = \
                 [re.escape(s) for s in
                  (self.initial_quote, self.final_quote,
                   self._escape_identifier(self.final_quote))]
        r = re.compile(
            r'(?:'
            r'(?:%(initial)s((?:%(escaped)s|[^%(final)s])+)%(final)s'
            r'|([^\.]+))(?=\.|$))+' %
            { 'initial': initial,
              'final': final,
              'escaped': escaped_final })
        return r

    def unformat_identifiers(self, identifiers):
        """Unpack 'schema.table.column'-like strings into components."""

        r = self._r_identifiers
        return [self._unescape_identifier(i)
                for i in [a or b for a, b in r.findall(identifiers)]]
