# orm/session.py
# Copyright (C) 2005-2012 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Provides the Session class and related utilities."""

import weakref
from itertools import chain
from sqlalchemy import util, sql, engine, log, exc as sa_exc
from sqlalchemy.sql import util as sql_util, expression
from sqlalchemy.orm import (
    SessionExtension, attributes, exc, query, unitofwork, util as mapperutil, state
    )
from sqlalchemy.orm.util import object_mapper as _object_mapper
from sqlalchemy.orm.util import class_mapper as _class_mapper
from sqlalchemy.orm.util import (
    _class_to_mapper, _state_mapper,
    )
from sqlalchemy.orm.mapper import Mapper, _none_set
from sqlalchemy.orm.unitofwork import UOWTransaction
from sqlalchemy.orm import identity
from sqlalchemy import event
from sqlalchemy.orm.events import SessionEvents

import sys

__all__ = ['Session', 'SessionTransaction', 'SessionExtension']


def sessionmaker(bind=None, class_=None, autoflush=True, autocommit=False,
                 expire_on_commit=True, **kwargs):
    """Generate a custom-configured :class:`.Session` class.

    The returned object is a subclass of :class:`.Session`, which, when instantiated
    with no arguments, uses the keyword arguments configured here as its
    constructor arguments.

    It is intended that the :func:`.sessionmaker()` function be called within the
    global scope of an application, and the returned class be made available
    to the rest of the application as the single class used to instantiate
    sessions.

    e.g.::

        # global scope
        Session = sessionmaker(autoflush=False)

        # later, in a local scope, create and use a session:
        sess = Session()

    Any keyword arguments sent to the constructor itself will override the
    "configured" keywords::

        Session = sessionmaker()

        # bind an individual session to a connection
        sess = Session(bind=connection)

    The class also includes a special classmethod ``configure()``, which
    allows additional configurational options to take place after the custom
    ``Session`` class has been generated.  This is useful particularly for
    defining the specific ``Engine`` (or engines) to which new instances of
    ``Session`` should be bound::

        Session = sessionmaker()
        Session.configure(bind=create_engine('sqlite:///foo.db'))

        sess = Session()
    
    For options, see the constructor options for :class:`.Session`.
    
    """
    kwargs['bind'] = bind
    kwargs['autoflush'] = autoflush
    kwargs['autocommit'] = autocommit
    kwargs['expire_on_commit'] = expire_on_commit

    if class_ is None:
        class_ = Session

    class Sess(object):
        def __init__(self, **local_kwargs):
            for k in kwargs:
                local_kwargs.setdefault(k, kwargs[k])
            super(Sess, self).__init__(**local_kwargs)

        @classmethod
        def configure(self, **new_kwargs):
            """(Re)configure the arguments for this sessionmaker.

            e.g.::

                Session = sessionmaker()

                Session.configure(bind=create_engine('sqlite://'))
            """
            kwargs.update(new_kwargs)


    return type("SessionMaker", (Sess, class_), {})


class SessionTransaction(object):
    """A Session-level transaction.

    This corresponds to one or more Core :class:`~.engine.base.Transaction`
    instances behind the scenes, with one :class:`~.engine.base.Transaction`
    per :class:`~.engine.base.Engine` in use.

    Direct usage of :class:`.SessionTransaction` is not typically 
    necessary as of SQLAlchemy 0.4; use the :meth:`.Session.rollback` and 
    :meth:`.Session.commit` methods on :class:`.Session` itself to 
    control the transaction.
    
    The current instance of :class:`.SessionTransaction` for a given
    :class:`.Session` is available via the :attr:`.Session.transaction`
    attribute.

    The :class:`.SessionTransaction` object is **not** thread-safe.

    See also:
    
    :meth:`.Session.rollback`
    
    :meth:`.Session.commit`

    :attr:`.Session.is_active`
    
    :meth:`.SessionEvents.after_commit`
    
    :meth:`.SessionEvents.after_rollback`
    
    :meth:`.SessionEvents.after_soft_rollback`
    
    .. index::
      single: thread safety; SessionTransaction

    """

    _rollback_exception = None

    def __init__(self, session, parent=None, nested=False):
        self.session = session
        self._connections = {}
        self._parent = parent
        self.nested = nested
        self._active = True
        self._prepared = False
        if not parent and nested:
            raise sa_exc.InvalidRequestError(
                "Can't start a SAVEPOINT transaction when no existing "
                "transaction is in progress")

        if self.session._enable_transaction_accounting:
            self._take_snapshot()

    @property
    def is_active(self):
        return self.session is not None and self._active

    def _assert_is_active(self):
        self._assert_is_open()
        if not self._active:
            if self._rollback_exception:
                raise sa_exc.InvalidRequestError(
                    "This Session's transaction has been rolled back "
                    "due to a previous exception during flush."
                    " To begin a new transaction with this Session, "
                    "first issue Session.rollback()."
                    " Original exception was: %s"
                    % self._rollback_exception
                )
            else:
                raise sa_exc.InvalidRequestError(
                    "This Session's transaction has been rolled back "
                    "by a nested rollback() call.  To begin a new "
                    "transaction, issue Session.rollback() first."
                    )

    def _assert_is_open(self, error_msg="The transaction is closed"):
        if self.session is None:
            raise sa_exc.ResourceClosedError(error_msg)

    @property
    def _is_transaction_boundary(self):
        return self.nested or not self._parent

    def connection(self, bindkey, **kwargs):
        self._assert_is_active()
        engine = self.session.get_bind(bindkey, **kwargs)
        return self._connection_for_bind(engine)

    def _begin(self, nested=False):
        self._assert_is_active()
        return SessionTransaction(
            self.session, self, nested=nested)

    def _iterate_parents(self, upto=None):
        if self._parent is upto:
            return (self,)
        else:
            if self._parent is None:
                raise sa_exc.InvalidRequestError(
                    "Transaction %s is not on the active transaction list" % (
                    upto))
            return (self,) + self._parent._iterate_parents(upto)

    def _take_snapshot(self):
        if not self._is_transaction_boundary:
            self._new = self._parent._new
            self._deleted = self._parent._deleted
            return

        if not self.session._flushing:
            self.session.flush()

        self._new = weakref.WeakKeyDictionary()
        self._deleted = weakref.WeakKeyDictionary()

    def _restore_snapshot(self):
        assert self._is_transaction_boundary

        for s in set(self._new).union(self.session._new):
            self.session._expunge_state(s)
            if s.key:
                del s.key

        for s in set(self._deleted).union(self.session._deleted):
            if s.deleted:
                #assert s in self._deleted
                del s.deleted
            self.session._update_impl(s)

        assert not self.session._deleted

        for s in self.session.identity_map.all_states():
            s.expire(s.dict, self.session.identity_map._modified)

    def _remove_snapshot(self):
        assert self._is_transaction_boundary

        if not self.nested and self.session.expire_on_commit:
            for s in self.session.identity_map.all_states():
                s.expire(s.dict, self.session.identity_map._modified)

    def _connection_for_bind(self, bind):
        self._assert_is_active()

        if bind in self._connections:
            return self._connections[bind][0]

        if self._parent:
            conn = self._parent._connection_for_bind(bind)
            if not self.nested:
                return conn
        else:
            if isinstance(bind, engine.Connection):
                conn = bind
                if conn.engine in self._connections:
                    raise sa_exc.InvalidRequestError(
                        "Session already has a Connection associated for the "
                        "given Connection's Engine")
            else:
                conn = bind.contextual_connect()

        if self.session.twophase and self._parent is None:
            transaction = conn.begin_twophase()
        elif self.nested:
            transaction = conn.begin_nested()
        else:
            transaction = conn.begin()

        self._connections[conn] = self._connections[conn.engine] = \
          (conn, transaction, conn is not bind)
        self.session.dispatch.after_begin(self.session, self, conn)
        return conn

    def prepare(self):
        if self._parent is not None or not self.session.twophase:
            raise sa_exc.InvalidRequestError(
                "Only root two phase transactions of can be prepared")
        self._prepare_impl()

    def _prepare_impl(self):
        self._assert_is_active()
        if self._parent is None or self.nested:
            self.session.dispatch.before_commit(self.session)

        stx = self.session.transaction
        if stx is not self:
            for subtransaction in stx._iterate_parents(upto=self):
                subtransaction.commit()

        if not self.session._flushing:
            self.session.flush()

        if self._parent is None and self.session.twophase:
            try:
                for t in set(self._connections.values()):
                    t[1].prepare()
            except:
                self.rollback()
                raise

        self._deactivate()
        self._prepared = True

    def commit(self):
        self._assert_is_open()
        if not self._prepared:
            self._prepare_impl()

        if self._parent is None or self.nested:
            for t in set(self._connections.values()):
                t[1].commit()

            self.session.dispatch.after_commit(self.session)

            if self.session._enable_transaction_accounting:
                self._remove_snapshot()

        self.close()
        return self._parent

    def rollback(self, _capture_exception=False):
        self._assert_is_open()

        stx = self.session.transaction
        if stx is not self:
            for subtransaction in stx._iterate_parents(upto=self):
                subtransaction.close()

        if self.is_active or self._prepared:
            for transaction in self._iterate_parents():
                if transaction._parent is None or transaction.nested:
                    transaction._rollback_impl()
                    transaction._deactivate()
                    break
                else:
                    transaction._deactivate()

        sess = self.session

        if self.session._enable_transaction_accounting and \
            not sess._is_clean():
            # if items were added, deleted, or mutated
            # here, we need to re-restore the snapshot
            util.warn(
                    "Session's state has been changed on "
                    "a non-active transaction - this state "
                    "will be discarded.")
            self._restore_snapshot()

        self.close()
        if self._parent and _capture_exception:
            self._parent._rollback_exception = sys.exc_info()[1]

        sess.dispatch.after_soft_rollback(sess, self)

        return self._parent

    def _rollback_impl(self):
        for t in set(self._connections.values()):
            t[1].rollback()

        if self.session._enable_transaction_accounting:
            self._restore_snapshot()

        self.session.dispatch.after_rollback(self.session)

    def _deactivate(self):
        self._active = False

    def close(self):
        self.session.transaction = self._parent
        if self._parent is None:
            for connection, transaction, autoclose in \
                set(self._connections.values()):
                if autoclose:
                    connection.close()
                else:
                    transaction.close()
            if not self.session.autocommit:
                self.session.begin()
        self._deactivate()
        self.session = None
        self._connections = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._assert_is_open("Cannot end transaction context. The transaction "
                                    "was closed from within the context")
        if self.session.transaction is None:
            return
        if type is None:
            try:
                self.commit()
            except:
                self.rollback()
                raise
        else:
            self.rollback()

class Session(object):
    """Manages persistence operations for ORM-mapped objects.

    The Session's usage paradigm is described at :ref:`session_toplevel`.


    """

    public_methods = (
        '__contains__', '__iter__', 'add', 'add_all', 'begin', 'begin_nested',
        'close', 'commit', 'connection', 'delete', 'execute', 'expire',
        'expire_all', 'expunge', 'expunge_all', 'flush', 'get_bind',
        'is_modified', 
        'merge', 'query', 'refresh', 'rollback', 
        'scalar')


    def __init__(self, bind=None, autoflush=True, expire_on_commit=True,
                _enable_transaction_accounting=True,
                 autocommit=False, twophase=False, 
                 weak_identity_map=True, binds=None, extension=None,
                 query_cls=query.Query):
        """Construct a new Session.

        See also the :func:`.sessionmaker` function which is used to 
        generate a :class:`.Session`-producing callable with a given
        set of arguments.

        :param autocommit: Defaults to ``False``. When ``True``, the ``Session``
          does not keep a persistent transaction running, and will acquire
          connections from the engine on an as-needed basis, returning them
          immediately after their use. Flushes will begin and commit (or possibly
          rollback) their own transaction if no transaction is present. When using
          this mode, the `session.begin()` method may be used to begin a
          transaction explicitly.

          Leaving it on its default value of ``False`` means that the ``Session``
          will acquire a connection and begin a transaction the first time it is
          used, which it will maintain persistently until ``rollback()``,
          ``commit()``, or ``close()`` is called. When the transaction is released
          by any of these methods, the ``Session`` is ready for the next usage,
          which will again acquire and maintain a new connection/transaction.

        :param autoflush: When ``True``, all query operations will issue a 
           ``flush()`` call to this ``Session`` before proceeding. This is a
           convenience feature so that ``flush()`` need not be called repeatedly
           in order for database queries to retrieve results. It's typical that
           ``autoflush`` is used in conjunction with ``autocommit=False``. In this
           scenario, explicit calls to ``flush()`` are rarely needed; you usually
           only need to call ``commit()`` (which flushes) to finalize changes.

        :param bind: An optional ``Engine`` or ``Connection`` to which this
           ``Session`` should be bound. When specified, all SQL operations
           performed by this session will execute via this connectable.

        :param binds: An optional dictionary which contains more granular "bind"
           information than the ``bind`` parameter provides. This dictionary can
           map individual ``Table`` instances as well as ``Mapper`` instances to
           individual ``Engine`` or ``Connection`` objects. Operations which
           proceed relative to a particular ``Mapper`` will consult this
           dictionary for the direct ``Mapper`` instance as well as the mapper's
           ``mapped_table`` attribute in order to locate an connectable to use.
           The full resolution is described in the ``get_bind()`` method of
           ``Session``. Usage looks like::

            Session = sessionmaker(binds={
                SomeMappedClass: create_engine('postgresql://engine1'),
                somemapper: create_engine('postgresql://engine2'),
                some_table: create_engine('postgresql://engine3'),
                })

          Also see the :meth:`.Session.bind_mapper` and :meth:`.Session.bind_table` methods.

        :param \class_: Specify an alternate class other than
           ``sqlalchemy.orm.session.Session`` which should be used by the returned
           class. This is the only argument that is local to the
           ``sessionmaker()`` function, and is not sent directly to the
           constructor for ``Session``.

        :param _enable_transaction_accounting:  Defaults to ``True``.  A
           legacy-only flag which when ``False`` disables *all* 0.5-style object
           accounting on transaction boundaries, including auto-expiry of
           instances on rollback and commit, maintenance of the "new" and
           "deleted" lists upon rollback, and autoflush of pending changes upon
           begin(), all of which are interdependent.

        :param expire_on_commit:  Defaults to ``True``. When ``True``, all
           instances will be fully expired after each ``commit()``, so that all
           attribute/object access subsequent to a completed transaction will load
           from the most recent database state.

        :param extension: An optional 
           :class:`~.SessionExtension` instance, or a list
           of such instances, which will receive pre- and post- commit and flush
           events, as well as a post-rollback event. **Deprecated.**
           Please see :class:`.SessionEvents`.

        :param query_cls:  Class which should be used to create new Query objects,
           as returned by the ``query()`` method. Defaults to
           :class:`~sqlalchemy.orm.query.Query`.

        :param twophase:  When ``True``, all transactions will be started as
            a "two phase" transaction, i.e. using the "two phase" semantics
            of the database in use along with an XID.  During a ``commit()``,
            after ``flush()`` has been issued for all attached databases, the
            ``prepare()`` method on each database's ``TwoPhaseTransaction`` will
            be called. This allows each database to roll back the entire
            transaction, before each transaction is committed.

        :param weak_identity_map:  Defaults to ``True`` - when set to 
           ``False``, objects placed in the :class:`.Session` will be 
           strongly referenced until explicitly removed or the 
           :class:`.Session` is closed.  **Deprecated** - this option
           is obsolete.

        """

        if weak_identity_map:
            self._identity_cls = identity.WeakInstanceDict
        else:
            util.warn_deprecated("weak_identity_map=False is deprecated.  "
                                    "This feature is not needed.")
            self._identity_cls = identity.StrongInstanceDict
        self.identity_map = self._identity_cls()

        self._new = {}   # InstanceState->object, strong refs object
        self._deleted = {}  # same
        self.bind = bind
        self.__binds = {}
        self._flushing = False
        self.transaction = None
        self.hash_key = _new_sessionid()
        self.autoflush = autoflush
        self.autocommit = autocommit
        self.expire_on_commit = expire_on_commit
        self._enable_transaction_accounting = _enable_transaction_accounting
        self.twophase = twophase
        self._query_cls = query_cls

        if extension:
            for ext in util.to_list(extension):
                SessionExtension._adapt_listener(self, ext)

        if binds is not None:
            for mapperortable, bind in binds.iteritems():
                if isinstance(mapperortable, (type, Mapper)):
                    self.bind_mapper(mapperortable, bind)
                else:
                    self.bind_table(mapperortable, bind)

        if not self.autocommit:
            self.begin()
        _sessions[self.hash_key] = self

    dispatch = event.dispatcher(SessionEvents)

    connection_callable = None

    transaction = None
    """The current active or inactive :class:`.SessionTransaction`."""

    def begin(self, subtransactions=False, nested=False):
        """Begin a transaction on this Session.

        If this Session is already within a transaction, either a plain
        transaction or nested transaction, an error is raised, unless
        ``subtransactions=True`` or ``nested=True`` is specified.

        The ``subtransactions=True`` flag indicates that this :meth:`~.Session.begin` 
        can create a subtransaction if a transaction is already in progress.
        For documentation on subtransactions, please see :ref:`session_subtransactions`.

        The ``nested`` flag begins a SAVEPOINT transaction and is equivalent
        to calling :meth:`~.Session.begin_nested`. For documentation on SAVEPOINT
        transactions, please see :ref:`session_begin_nested`.

        """
        if self.transaction is not None:
            if subtransactions or nested:
                self.transaction = self.transaction._begin(
                                        nested=nested)
            else:
                raise sa_exc.InvalidRequestError(
                    "A transaction is already begun.  Use subtransactions=True "
                    "to allow subtransactions.")
        else:
            self.transaction = SessionTransaction(
                self, nested=nested)
        return self.transaction  # needed for __enter__/__exit__ hook

    def begin_nested(self):
        """Begin a `nested` transaction on this Session.

        The target database(s) must support SQL SAVEPOINTs or a
        SQLAlchemy-supported vendor implementation of the idea.

        For documentation on SAVEPOINT
        transactions, please see :ref:`session_begin_nested`.

        """
        return self.begin(nested=True)

    def rollback(self):
        """Rollback the current transaction in progress.

        If no transaction is in progress, this method is a pass-through.

        This method rolls back the current transaction or nested transaction
        regardless of subtransactions being in effect.  All subtransactions up
        to the first real transaction are closed.  Subtransactions occur when
        begin() is called multiple times.

        """
        if self.transaction is None:
            pass
        else:
            self.transaction.rollback()

    def commit(self):
        """Flush pending changes and commit the current transaction.

        If no transaction is in progress, this method raises an
        InvalidRequestError.

        By default, the :class:`.Session` also expires all database
        loaded state on all ORM-managed attributes after transaction commit.
        This so that subsequent operations load the most recent 
        data from the database.   This behavior can be disabled using
        the ``expire_on_commit=False`` option to :func:`.sessionmaker` or
        the :class:`.Session` constructor.

        If a subtransaction is in effect (which occurs when begin() is called
        multiple times), the subtransaction will be closed, and the next call
        to ``commit()`` will operate on the enclosing transaction.

        For a session configured with autocommit=False, a new transaction will
        be begun immediately after the commit, but note that the newly begun
        transaction does *not* use any connection resources until the first
        SQL is actually emitted.

        """
        if self.transaction is None:
            if not self.autocommit:
                self.begin()
            else:
                raise sa_exc.InvalidRequestError("No transaction is begun.")

        self.transaction.commit()

    def prepare(self):
        """Prepare the current transaction in progress for two phase commit.

        If no transaction is in progress, this method raises an
        InvalidRequestError.

        Only root transactions of two phase sessions can be prepared. If the
        current transaction is not such, an InvalidRequestError is raised.

        """
        if self.transaction is None:
            if not self.autocommit:
                self.begin()
            else:
                raise sa_exc.InvalidRequestError("No transaction is begun.")

        self.transaction.prepare()

    def connection(self, mapper=None, clause=None, 
                        bind=None, 
                        close_with_result=False, 
                        **kw):
        """Return a :class:`.Connection` object corresponding to this 
        :class:`.Session` object's transactional state.

        If this :class:`.Session` is configured with ``autocommit=False``,
        either the :class:`.Connection` corresponding to the current transaction
        is returned, or if no transaction is in progress, a new one is begun
        and the :class:`.Connection` returned (note that no transactional state
        is established with the DBAPI until the first SQL statement is emitted).
        
        Alternatively, if this :class:`.Session` is configured with ``autocommit=True``,
        an ad-hoc :class:`.Connection` is returned using :meth:`.Engine.contextual_connect` 
        on the underlying :class:`.Engine`.

        Ambiguity in multi-bind or unbound :class:`.Session` objects can be resolved through
        any of the optional keyword arguments.   This ultimately makes usage of the 
        :meth:`.get_bind` method for resolution.

        :param bind:
          Optional :class:`.Engine` to be used as the bind.  If
          this engine is already involved in an ongoing transaction,
          that connection will be used.  This argument takes precedence
          over ``mapper``, ``clause``.

        :param mapper:
          Optional :func:`.mapper` mapped class, used to identify
          the appropriate bind.  This argument takes precedence over
          ``clause``.

        :param clause:
            A :class:`.ClauseElement` (i.e. :func:`~.sql.expression.select`, 
            :func:`~.sql.expression.text`, 
            etc.) which will be used to locate a bind, if a bind
            cannot otherwise be identified.

        :param close_with_result: Passed to :meth:`Engine.connect`, indicating
          the :class:`.Connection` should be considered "single use", automatically
          closing when the first result set is closed.  This flag only has 
          an effect if this :class:`.Session` is configured with ``autocommit=True``
          and does not already have a  transaction in progress.

        :param \**kw:
          Additional keyword arguments are sent to :meth:`get_bind()`,
          allowing additional arguments to be passed to custom 
          implementations of :meth:`get_bind`.

        """
        if bind is None:
            bind = self.get_bind(mapper, clause=clause, **kw)

        return self._connection_for_bind(bind, 
                                        close_with_result=close_with_result)

    def _connection_for_bind(self, engine, **kwargs):
        if self.transaction is not None:
            return self.transaction._connection_for_bind(engine)
        else:
            return engine.contextual_connect(**kwargs)

    def execute(self, clause, params=None, mapper=None, bind=None, **kw):
        """Execute a clause within the current transaction.

        Returns a :class:`.ResultProxy` representing
        results of the statement execution, in the same manner as that of an
        :class:`.Engine` or
        :class:`.Connection`.

        :meth:`~.Session.execute` accepts any executable clause construct, such
        as :func:`~.sql.expression.select`,
        :func:`~.sql.expression.insert`,
        :func:`~.sql.expression.update`,
        :func:`~.sql.expression.delete`, and
        :func:`~.sql.expression.text`, and additionally accepts
        plain strings that represent SQL statements. If a plain string is
        passed, it is first converted to a
        :func:`~.sql.expression.text` construct, which here means
        that bind parameters should be specified using the format ``:param``.
        If raw DBAPI statement execution is desired, use :meth:`.Session.connection`
        to acquire a :class:`.Connection`, then call its :meth:`~.Connection.execute`
        method.

        The statement is executed within the current transactional context of
        this :class:`.Session`, using the same behavior as that of
        the :meth:`.Session.connection` method to determine the active
        :class:`.Connection`.   The ``close_with_result`` flag is
        set to ``True`` so that an ``autocommit=True`` :class:`.Session`
        with no active transaction will produce a result that auto-closes
        the underlying :class:`.Connection`.
        
        :param clause:
            A :class:`.ClauseElement` (i.e. :func:`~.sql.expression.select`, 
            :func:`~.sql.expression.text`, etc.) or string SQL statement to be executed.  The clause
            will also be used to locate a bind, if this :class:`.Session`
            is not bound to a single engine already, and the ``mapper``
            and ``bind`` arguments are not passed.

        :param params:
            Optional dictionary of bind names mapped to values.

        :param mapper:
          Optional :func:`.mapper` or mapped class, used to identify
          the appropriate bind.  This argument takes precedence over
          ``clause`` when locating a bind.

        :param bind:
          Optional :class:`.Engine` to be used as the bind.  If
          this engine is already involved in an ongoing transaction,
          that connection will be used.  This argument takes
          precedence over ``mapper`` and ``clause`` when locating
          a bind.
          
        :param \**kw:
          Additional keyword arguments are sent to :meth:`get_bind()`,
          allowing additional arguments to be passed to custom 
          implementations of :meth:`get_bind`.

        """
        clause = expression._literal_as_text(clause)

        if bind is None:
            bind = self.get_bind(mapper, clause=clause, **kw)

        return self._connection_for_bind(bind, close_with_result=True).execute(
            clause, params or {})

    def scalar(self, clause, params=None, mapper=None, bind=None, **kw):
        """Like :meth:`~.Session.execute` but return a scalar result."""

        return self.execute(clause, params=params, mapper=mapper, bind=bind, **kw).scalar()

    def close(self):
        """Close this Session.

        This clears all items and ends any transaction in progress.

        If this session were created with ``autocommit=False``, a new
        transaction is immediately begun.  Note that this new transaction does
        not use any connection resources until they are first needed.

        """
        self.expunge_all()
        if self.transaction is not None:
            for transaction in self.transaction._iterate_parents():
                transaction.close()

    @classmethod
    def close_all(cls):
        """Close *all* sessions in memory."""

        for sess in _sessions.values():
            sess.close()

    def expunge_all(self):
        """Remove all object instances from this ``Session``.

        This is equivalent to calling ``expunge(obj)`` on all objects in this
        ``Session``.

        """
        for state in self.identity_map.all_states() + list(self._new):
            state.detach()

        self.identity_map = self._identity_cls()
        self._new = {}
        self._deleted = {}

    # TODO: need much more test coverage for bind_mapper() and similar !
    # TODO: + crystalize + document resolution order vis. bind_mapper/bind_table

    def bind_mapper(self, mapper, bind):
        """Bind operations for a mapper to a Connectable.

        mapper
          A mapper instance or mapped class

        bind
          Any Connectable: a ``Engine`` or ``Connection``.

        All subsequent operations involving this mapper will use the given
        `bind`.

        """
        if isinstance(mapper, type):
            mapper = _class_mapper(mapper)

        self.__binds[mapper.base_mapper] = bind
        for t in mapper._all_tables:
            self.__binds[t] = bind

    def bind_table(self, table, bind):
        """Bind operations on a Table to a Connectable.

        table
          A ``Table`` instance

        bind
          Any Connectable: a ``Engine`` or ``Connection``.

        All subsequent operations involving this ``Table`` will use the
        given `bind`.

        """
        self.__binds[table] = bind

    def get_bind(self, mapper=None, clause=None):
        """Return a "bind" to which this :class:`.Session` is bound.
        
        The "bind" is usually an instance of :class:`.Engine`, 
        except in the case where the :class:`.Session` has been
        explicitly bound directly to a :class:`.Connection`.

        For a multiply-bound or unbound :class:`.Session`, the 
        ``mapper`` or ``clause`` arguments are used to determine the 
        appropriate bind to return.
        
        Note that the "mapper" argument is usually present
        when :meth:`.Session.get_bind` is called via an ORM
        operation such as a :meth:`.Session.query`, each 
        individual INSERT/UPDATE/DELETE operation within a 
        :meth:`.Session.flush`, call, etc.
        
        The order of resolution is:
        
        1. if mapper given and session.binds is present,
           locate a bind based on mapper.
        2. if clause given and session.binds is present,
           locate a bind based on :class:`.Table` objects
           found in the given clause present in session.binds.
        3. if session.bind is present, return that.
        4. if clause given, attempt to return a bind 
           linked to the :class:`.MetaData` ultimately
           associated with the clause.
        5. if mapper given, attempt to return a bind
           linked to the :class:`.MetaData` ultimately 
           associated with the :class:`.Table` or other
           selectable to which the mapper is mapped.
        6. No bind can be found, :class:`.UnboundExecutionError`
           is raised.
         
        :param mapper:
          Optional :func:`.mapper` mapped class or instance of
          :class:`.Mapper`.   The bind can be derived from a :class:`.Mapper`
          first by consulting the "binds" map associated with this
          :class:`.Session`, and secondly by consulting the :class:`.MetaData`
          associated with the :class:`.Table` to which the :class:`.Mapper`
          is mapped for a bind.

        :param clause:
            A :class:`.ClauseElement` (i.e. :func:`~.sql.expression.select`, 
            :func:`~.sql.expression.text`, 
            etc.).  If the ``mapper`` argument is not present or could not produce
            a bind, the given expression construct will be searched for a bound
            element, typically a :class:`.Table` associated with bound 
            :class:`.MetaData`.

        """
        if mapper is clause is None:
            if self.bind:
                return self.bind
            else:
                raise sa_exc.UnboundExecutionError(
                    "This session is not bound to a single Engine or "
                    "Connection, and no context was provided to locate "
                    "a binding.")

        c_mapper = mapper is not None and _class_to_mapper(mapper) or None

        # manually bound?
        if self.__binds:
            if c_mapper:
                if c_mapper.base_mapper in self.__binds:
                    return self.__binds[c_mapper.base_mapper]
                elif c_mapper.mapped_table in self.__binds:
                    return self.__binds[c_mapper.mapped_table]
            if clause is not None:
                for t in sql_util.find_tables(clause, include_crud=True):
                    if t in self.__binds:
                        return self.__binds[t]

        if self.bind:
            return self.bind

        if isinstance(clause, sql.expression.ClauseElement) and clause.bind:
            return clause.bind

        if c_mapper and c_mapper.mapped_table.bind:
            return c_mapper.mapped_table.bind

        context = []
        if mapper is not None:
            context.append('mapper %s' % c_mapper)
        if clause is not None:
            context.append('SQL expression')

        raise sa_exc.UnboundExecutionError(
            "Could not locate a bind configured on %s or this Session" % (
            ', '.join(context)))

    def query(self, *entities, **kwargs):
        """Return a new ``Query`` object corresponding to this ``Session``."""

        return self._query_cls(entities, self, **kwargs)

    @property
    @util.contextmanager
    def no_autoflush(self):
        """Return a context manager that disables autoflush.
        
        e.g.::
        
            with session.no_autoflush:
                
                some_object = SomeClass()
                session.add(some_object)
                # won't autoflush
                some_object.related_thing = session.query(SomeRelated).first()
        
        Operations that proceed within the ``with:`` block
        will not be subject to flushes occurring upon query
        access.  This is useful when initializing a series
        of objects which involve existing database queries,
        where the uncompleted object should not yet be flushed.
        
        New in 0.7.6.

        """
        autoflush = self.autoflush
        self.autoflush = False
        yield self
        self.autoflush = autoflush

    def _autoflush(self):
        if self.autoflush and not self._flushing:
            self.flush()

    def _finalize_loaded(self, states):
        for state, dict_ in states.items():
            state.commit_all(dict_, self.identity_map)

    def refresh(self, instance, attribute_names=None, lockmode=None):
        """Expire and refresh the attributes on the given instance.

        A query will be issued to the database and all attributes will be
        refreshed with their current database value.

        Lazy-loaded relational attributes will remain lazily loaded, so that
        the instance-wide refresh operation will be followed immediately by
        the lazy load of that attribute.

        Eagerly-loaded relational attributes will eagerly load within the
        single refresh operation.

        Note that a highly isolated transaction will return the same values as
        were previously read in that same transaction, regardless of changes
        in database state outside of that transaction - usage of
        :meth:`~Session.refresh` usually only makes sense if non-ORM SQL
        statement were emitted in the ongoing transaction, or if autocommit
        mode is turned on.

        :param attribute_names: optional.  An iterable collection of
          string attribute names indicating a subset of attributes to 
          be refreshed.

        :param lockmode: Passed to the :class:`~sqlalchemy.orm.query.Query` 
          as used by :meth:`~sqlalchemy.orm.query.Query.with_lockmode`.

        """
        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)

        self._expire_state(state, attribute_names)

        if self.query(_object_mapper(instance))._load_on_ident(
                state.key, refresh_state=state,
                lockmode=lockmode,
                only_load_props=attribute_names) is None:
            raise sa_exc.InvalidRequestError(
                "Could not refresh instance '%s'" %
                mapperutil.instance_str(instance))

    def expire_all(self):
        """Expires all persistent instances within this Session.

        When any attributes on a persistent instance is next accessed, 
        a query will be issued using the
        :class:`.Session` object's current transactional context in order to
        load all expired attributes for the given instance.   Note that
        a highly isolated transaction will return the same values as were 
        previously read in that same transaction, regardless of changes
        in database state outside of that transaction.

        To expire individual objects and individual attributes 
        on those objects, use :meth:`Session.expire`.

        The :class:`.Session` object's default behavior is to 
        expire all state whenever the :meth:`Session.rollback`
        or :meth:`Session.commit` methods are called, so that new
        state can be loaded for the new transaction.   For this reason,
        calling :meth:`Session.expire_all` should not be needed when 
        autocommit is ``False``, assuming the transaction is isolated.

        """
        for state in self.identity_map.all_states():
            state.expire(state.dict, self.identity_map._modified)

    def expire(self, instance, attribute_names=None):
        """Expire the attributes on an instance.

        Marks the attributes of an instance as out of date. When an expired
        attribute is next accessed, a query will be issued to the
        :class:`.Session` object's current transactional context in order to
        load all expired attributes for the given instance.   Note that
        a highly isolated transaction will return the same values as were 
        previously read in that same transaction, regardless of changes
        in database state outside of that transaction.

        To expire all objects in the :class:`.Session` simultaneously,
        use :meth:`Session.expire_all`.

        The :class:`.Session` object's default behavior is to 
        expire all state whenever the :meth:`Session.rollback`
        or :meth:`Session.commit` methods are called, so that new
        state can be loaded for the new transaction.   For this reason,
        calling :meth:`Session.expire` only makes sense for the specific
        case that a non-ORM SQL statement was emitted in the current
        transaction.

        :param instance: The instance to be refreshed.
        :param attribute_names: optional list of string attribute names
          indicating a subset of attributes to be expired.

        """
        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)
        self._expire_state(state, attribute_names)

    def _expire_state(self, state, attribute_names):
        self._validate_persistent(state)
        if attribute_names:
            state.expire_attributes(state.dict, attribute_names)
        else:
            # pre-fetch the full cascade since the expire is going to
            # remove associations
            cascaded = list(state.manager.mapper.cascade_iterator(
                                            'refresh-expire', state))
            self._conditional_expire(state)
            for o, m, st_, dct_ in cascaded:
                self._conditional_expire(st_)

    def _conditional_expire(self, state):
        """Expire a state if persistent, else expunge if pending"""

        if state.key:
            state.expire(state.dict, self.identity_map._modified)
        elif state in self._new:
            self._new.pop(state)
            state.detach()

    @util.deprecated("0.7", "The non-weak-referencing identity map "
                        "feature is no longer needed.")
    def prune(self):
        """Remove unreferenced instances cached in the identity map.

        Note that this method is only meaningful if "weak_identity_map" is set
        to False.  The default weak identity map is self-pruning.

        Removes any object in this Session's identity map that is not
        referenced in user code, modified, new or scheduled for deletion.
        Returns the number of objects pruned.

        """
        return self.identity_map.prune()

    def expunge(self, instance):
        """Remove the `instance` from this ``Session``.

        This will free all internal references to the instance.  Cascading
        will be applied according to the *expunge* cascade rule.

        """
        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)
        if state.session_id is not self.hash_key:
            raise sa_exc.InvalidRequestError(
                "Instance %s is not present in this Session" %
                mapperutil.state_str(state))

        cascaded = list(state.manager.mapper.cascade_iterator(
                                    'expunge', state))
        self._expunge_state(state)
        for o, m, st_, dct_ in cascaded:
            self._expunge_state(st_)

    def _expunge_state(self, state):
        if state in self._new:
            self._new.pop(state)
            state.detach()
        elif self.identity_map.contains_state(state):
            self.identity_map.discard(state)
            self._deleted.pop(state, None)
            state.detach()
        elif self.transaction:
            self.transaction._deleted.pop(state, None)

    def _register_newly_persistent(self, state):
        mapper = _state_mapper(state)

        # prevent against last minute dereferences of the object
        obj = state.obj()
        if obj is not None:

            instance_key = mapper._identity_key_from_state(state)

            if _none_set.issubset(instance_key[1]) and \
                not mapper.allow_partial_pks or \
                _none_set.issuperset(instance_key[1]):
                raise exc.FlushError(
                    "Instance %s has a NULL identity key.  If this is an "
                    "auto-generated value, check that the database table "
                    "allows generation of new primary key values, and that "
                    "the mapped Column object is configured to expect these "
                    "generated values.  Ensure also that this flush() is "
                    "not occurring at an inappropriate time, such as within "
                    "a load() event." % mapperutil.state_str(state)
                )

            if state.key is None:
                state.key = instance_key
            elif state.key != instance_key:
                # primary key switch. use discard() in case another 
                # state has already replaced this one in the identity 
                # map (see test/orm/test_naturalpks.py ReversePKsTest)
                self.identity_map.discard(state)
                state.key = instance_key

            self.identity_map.replace(state)
            state.commit_all(state.dict, self.identity_map)

        # remove from new last, might be the last strong ref
        if state in self._new:
            if self._enable_transaction_accounting and self.transaction:
                self.transaction._new[state] = True
            self._new.pop(state)

    def _remove_newly_deleted(self, state):
        if self._enable_transaction_accounting and self.transaction:
            self.transaction._deleted[state] = True

        self.identity_map.discard(state)
        self._deleted.pop(state, None)
        state.deleted = True

    def add(self, instance):
        """Place an object in the ``Session``.

        Its state will be persisted to the database on the next flush
        operation.

        Repeated calls to ``add()`` will be ignored. The opposite of ``add()``
        is ``expunge()``.

        """
        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)

        self._save_or_update_state(state)

    def add_all(self, instances):
        """Add the given collection of instances to this ``Session``."""

        for instance in instances:
            self.add(instance)

    def _save_or_update_state(self, state):
        self._save_or_update_impl(state)

        mapper = _state_mapper(state)
        for o, m, st_, dct_ in mapper.cascade_iterator(
                                    'save-update', 
                                    state, 
                                    halt_on=self._contains_state):
            self._save_or_update_impl(st_)

    def delete(self, instance):
        """Mark an instance as deleted.

        The database delete operation occurs upon ``flush()``.

        """
        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)

        if state.key is None:
            raise sa_exc.InvalidRequestError(
                "Instance '%s' is not persisted" %
                mapperutil.state_str(state))

        if state in self._deleted:
            return

        # ensure object is attached to allow the 
        # cascade operation to load deferred attributes
        # and collections
        self._attach(state)

        # grab the cascades before adding the item to the deleted list
        # so that autoflush does not delete the item
        # the strong reference to the instance itself is significant here
        cascade_states = list(state.manager.mapper.cascade_iterator(
                                            'delete', state))

        self._deleted[state] = state.obj()
        self.identity_map.add(state)

        for o, m, st_, dct_ in cascade_states:
            self._delete_impl(st_)

    def merge(self, instance, load=True, **kw):
        """Copy the state an instance onto the persistent instance with the
        same identifier.

        If there is no persistent instance currently associated with the
        session, it will be loaded.  Return the persistent instance. If the
        given instance is unsaved, save a copy of and return it as a newly
        persistent instance. The given instance does not become associated
        with the session.

        This operation cascades to associated instances if the association is
        mapped with ``cascade="merge"``.

        See :ref:`unitofwork_merging` for a detailed discussion of merging.

        """
        if 'dont_load' in kw:
            load = not kw['dont_load']
            util.warn_deprecated('dont_load=True has been renamed to '
                                 'load=False.')

        _recursive = {}

        if load:
            # flush current contents if we expect to load data
            self._autoflush()

        _object_mapper(instance) # verify mapped
        autoflush = self.autoflush
        try:
            self.autoflush = False
            return self._merge(
                            attributes.instance_state(instance), 
                            attributes.instance_dict(instance), 
                            load=load, _recursive=_recursive)
        finally:
            self.autoflush = autoflush

    def _merge(self, state, state_dict, load=True, _recursive=None):
        mapper = _state_mapper(state)
        if state in _recursive:
            return _recursive[state]

        new_instance = False
        key = state.key

        if key is None:
            if not load:
                raise sa_exc.InvalidRequestError(
                    "merge() with load=False option does not support "
                    "objects transient (i.e. unpersisted) objects.  flush() "
                    "all changes on mapped instances before merging with "
                    "load=False.")
            key = mapper._identity_key_from_state(state)

        if key in self.identity_map:
            merged = self.identity_map[key]

        elif not load:
            if state.modified:
                raise sa_exc.InvalidRequestError(
                    "merge() with load=False option does not support "
                    "objects marked as 'dirty'.  flush() all changes on "
                    "mapped instances before merging with load=False.")
            merged = mapper.class_manager.new_instance()
            merged_state = attributes.instance_state(merged)
            merged_state.key = key
            self._update_impl(merged_state)
            new_instance = True

        elif not _none_set.issubset(key[1]) or \
                    (mapper.allow_partial_pks and 
                    not _none_set.issuperset(key[1])):
            merged = self.query(mapper.class_).get(key[1])
        else:
            merged = None

        if merged is None:
            merged = mapper.class_manager.new_instance()
            merged_state = attributes.instance_state(merged)
            merged_dict = attributes.instance_dict(merged)
            new_instance = True
            self._save_or_update_state(merged_state)
        else:
            merged_state = attributes.instance_state(merged)
            merged_dict = attributes.instance_dict(merged)

        _recursive[state] = merged

        # check that we didn't just pull the exact same
        # state out.
        if state is not merged_state:
            # version check if applicable
            if mapper.version_id_col is not None:
                existing_version = mapper._get_state_attr_by_column(
                            state, 
                            state_dict, 
                            mapper.version_id_col,
                            passive=attributes.PASSIVE_NO_INITIALIZE)

                merged_version = mapper._get_state_attr_by_column(
                            merged_state, 
                            merged_dict, 
                            mapper.version_id_col,
                            passive=attributes.PASSIVE_NO_INITIALIZE)

                if existing_version is not attributes.PASSIVE_NO_RESULT and \
                    merged_version is not attributes.PASSIVE_NO_RESULT and \
                    existing_version != merged_version:
                    raise exc.StaleDataError(
                            "Version id '%s' on merged state %s "
                            "does not match existing version '%s'. "
                            "Leave the version attribute unset when "
                            "merging to update the most recent version."
                            % (
                                existing_version,
                                mapperutil.state_str(merged_state),
                                merged_version
                            ))

            merged_state.load_path = state.load_path
            merged_state.load_options = state.load_options

            for prop in mapper.iterate_properties:
                prop.merge(self, state, state_dict, 
                                merged_state, merged_dict, 
                                load, _recursive)

        if not load:
            # remove any history
            merged_state.commit_all(merged_dict, self.identity_map)

        if new_instance:
            merged_state.manager.dispatch.load(merged_state, None)
        return merged

    @classmethod
    def identity_key(cls, *args, **kwargs):
        return mapperutil.identity_key(*args, **kwargs)

    @classmethod
    def object_session(cls, instance):
        """Return the ``Session`` to which an object belongs."""

        return object_session(instance)

    def _validate_persistent(self, state):
        if not self.identity_map.contains_state(state):
            raise sa_exc.InvalidRequestError(
                "Instance '%s' is not persistent within this Session" %
                mapperutil.state_str(state))

    def _save_impl(self, state):
        if state.key is not None:
            raise sa_exc.InvalidRequestError(
                "Object '%s' already has an identity - it can't be registered "
                "as pending" % mapperutil.state_str(state))

        self._attach(state)
        if state not in self._new:
            self._new[state] = state.obj()
            state.insert_order = len(self._new)

    def _update_impl(self, state):
        if (self.identity_map.contains_state(state) and
            state not in self._deleted):
            return

        if state.key is None:
            raise sa_exc.InvalidRequestError(
                "Instance '%s' is not persisted" %
                mapperutil.state_str(state))

        if state.deleted:
            raise sa_exc.InvalidRequestError(
                "Instance '%s' has been deleted.  Use the make_transient() "
                "function to send this object back to the transient state." %
                mapperutil.state_str(state)
            )
        self._attach(state)
        self._deleted.pop(state, None)
        self.identity_map.add(state)

    def _save_or_update_impl(self, state):
        if state.key is None:
            self._save_impl(state)
        else:
            self._update_impl(state)

    def _delete_impl(self, state):
        if state in self._deleted:
            return

        if state.key is None:
            return

        self._attach(state)
        self._deleted[state] = state.obj()
        self.identity_map.add(state)

    def _attach(self, state):
        if state.key and \
            state.key in self.identity_map and \
            not self.identity_map.contains_state(state):
            raise sa_exc.InvalidRequestError("Can't attach instance "
                    "%s; another instance with key %s is already "
                    "present in this session."
                    % (mapperutil.state_str(state), state.key))

        if state.session_id and \
                state.session_id is not self.hash_key and \
                state.session_id in _sessions:
            raise sa_exc.InvalidRequestError(
                "Object '%s' is already attached to session '%s' "
                "(this is '%s')" % (mapperutil.state_str(state),
                                    state.session_id, self.hash_key))

        if state.session_id != self.hash_key:
            state.session_id = self.hash_key
            if self.dispatch.after_attach:
                self.dispatch.after_attach(self, state.obj())

    def __contains__(self, instance):
        """Return True if the instance is associated with this session.

        The instance may be pending or persistent within the Session for a
        result of True.

        """
        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)
        return self._contains_state(state)

    def __iter__(self):
        """Iterate over all pending or persistent instances within this Session."""

        return iter(list(self._new.values()) + self.identity_map.values())

    def _contains_state(self, state):
        return state in self._new or self.identity_map.contains_state(state)

    def flush(self, objects=None):
        """Flush all the object changes to the database.

        Writes out all pending object creations, deletions and modifications
        to the database as INSERTs, DELETEs, UPDATEs, etc.  Operations are
        automatically ordered by the Session's unit of work dependency
        solver.

        Database operations will be issued in the current transactional
        context and do not affect the state of the transaction, unless an
        error occurs, in which case the entire transaction is rolled back. 
        You may flush() as often as you like within a transaction to move
        changes from Python to the database's transaction buffer.

        For ``autocommit`` Sessions with no active manual transaction, flush()
        will create a transaction on the fly that surrounds the entire set of
        operations int the flush.

        objects
          Optional; a list or tuple collection.  Restricts the flush operation
          to only these objects, rather than all pending changes.
          Deprecated - this flag prevents the session from properly maintaining
          accounting among inter-object relations and can cause invalid results.

        """

        if objects:
            util.warn_deprecated(
                "The 'objects' argument to session.flush() is deprecated; "
                "Please do not add objects to the session which should not "
                "yet be persisted.")

        if self._flushing:
            raise sa_exc.InvalidRequestError("Session is already flushing")

        if self._is_clean():
            return
        try:
            self._flushing = True
            self._flush(objects)
        finally:
            self._flushing = False

    def _is_clean(self):
        return not self.identity_map.check_modified() and \
                not self._deleted and \
                not self._new

    def _flush(self, objects=None):

        dirty = self._dirty_states
        if not dirty and not self._deleted and not self._new:
            self.identity_map._modified.clear()
            return

        flush_context = UOWTransaction(self)

        if self.dispatch.before_flush:
            self.dispatch.before_flush(self, flush_context, objects)
            # re-establish "dirty states" in case the listeners
            # added
            dirty = self._dirty_states

        deleted = set(self._deleted)
        new = set(self._new)

        dirty = set(dirty).difference(deleted)

        # create the set of all objects we want to operate upon
        if objects:
            # specific list passed in
            objset = set()
            for o in objects:
                try:
                    state = attributes.instance_state(o)
                except exc.NO_STATE:
                    raise exc.UnmappedInstanceError(o)
                objset.add(state)
        else:
            objset = None

        # store objects whose fate has been decided
        processed = set()

        # put all saves/updates into the flush context.  detect top-level
        # orphans and throw them into deleted.
        if objset:
            proc = new.union(dirty).intersection(objset).difference(deleted)
        else:
            proc = new.union(dirty).difference(deleted)

        for state in proc:
            is_orphan = _state_mapper(state)._is_orphan(state) and state.has_identity
            flush_context.register_object(state, isdelete=is_orphan)
            processed.add(state)

        # put all remaining deletes into the flush context.
        if objset:
            proc = deleted.intersection(objset).difference(processed)
        else:
            proc = deleted.difference(processed)
        for state in proc:
            flush_context.register_object(state, isdelete=True)

        if not flush_context.has_work:
            return

        flush_context.transaction = transaction = self.begin(
            subtransactions=True)
        try:
            flush_context.execute()

            self.dispatch.after_flush(self, flush_context)

            flush_context.finalize_flush_changes()

            # useful assertions:
            #if not objects:
            #    assert not self.identity_map._modified
            #else:
            #    assert self.identity_map._modified == \
            #            self.identity_map._modified.difference(objects)

            self.dispatch.after_flush_postexec(self, flush_context)

            transaction.commit()

        except:
            transaction.rollback(_capture_exception=True)
            raise


    def is_modified(self, instance, include_collections=True, 
                            passive=attributes.PASSIVE_OFF):
        """Return ``True`` if the given instance has locally 
        modified attributes.

        This method retrieves the history for each instrumented
        attribute on the instance and performs a comparison of the current
        value to its previously committed value, if any.
        
        It is in effect a more expensive and accurate
        version of checking for the given instance in the 
        :attr:`.Session.dirty` collection; a full test for 
        each attribute's net "dirty" status is performed.
        
        E.g.::
        
            return session.is_modified(someobject, passive=True)
            
        .. note:: 
          
           In SQLAlchemy 0.7 and earlier, the ``passive`` 
           flag should **always** be explicitly set to ``True``. 
           The current default value of :data:`.attributes.PASSIVE_OFF`
           for this flag is incorrect, in that it loads unloaded
           collections and attributes which by definition 
           have no modified state, and furthermore trips off 
           autoflush which then causes all subsequent, possibly
           modified attributes to lose their modified state.   
           The default value of the flag will be changed in 0.8.
           
        A few caveats to this method apply:

        * Instances present in the :attr:`.Session.dirty` collection may report 
          ``False`` when tested with this method.  This is because 
          the object may have received change events via attribute
          mutation, thus placing it in :attr:`.Session.dirty`, 
          but ultimately the state is the same as that loaded from
          the database, resulting in no net change here.
        * Scalar attributes may not have recorded the previously set
          value when a new value was applied, if the attribute was not loaded,
          or was expired, at the time the new value was received - in these
          cases, the attribute is assumed to have a change, even if there is
          ultimately no net change against its database value. SQLAlchemy in
          most cases does not need the "old" value when a set event occurs, so
          it skips the expense of a SQL call if the old value isn't present,
          based on the assumption that an UPDATE of the scalar value is
          usually needed, and in those few cases where it isn't, is less
          expensive on average than issuing a defensive SELECT. 

          The "old" value is fetched unconditionally only if the attribute
          container has the ``active_history`` flag set to ``True``. This flag
          is set typically for primary key attributes and scalar object references
          that are not a simple many-to-one.  To set this flag for 
          any arbitrary mapped column, use the ``active_history`` argument
          with :func:`.column_property`.
          
        :param instance: mapped instance to be tested for pending changes.
        :param include_collections: Indicates if multivalued collections should be
         included in the operation.  Setting this to ``False`` is a way to detect
         only local-column based properties (i.e. scalar columns or many-to-one
         foreign keys) that would result in an UPDATE for this instance upon
         flush.
        :param passive: Indicates if unloaded attributes and 
         collections should be loaded in the course of performing 
         this test.  If set to ``False``, or left at its default
         value of :data:`.PASSIVE_OFF`, unloaded attributes
         will be loaded.  If set to ``True`` or 
         :data:`.PASSIVE_NO_INITIALIZE`, unloaded 
         collections and attributes will remain unloaded.  As 
         noted previously, the existence of this flag here
         is a bug, as unloaded attributes by definition have 
         no changes, and the load operation also triggers an
         autoflush which then cancels out subsequent changes.
         This flag should **always be set to 
         True**.  In 0.8 the flag will be deprecated and the default
         set to ``True``.


        """
        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)
        dict_ = state.dict

        if passive is True:
            passive = attributes.PASSIVE_NO_INITIALIZE
        elif passive is False:
            passive = attributes.PASSIVE_OFF

        for attr in state.manager.attributes:
            if \
                (
                    not include_collections and 
                    hasattr(attr.impl, 'get_collection')
                ) or not hasattr(attr.impl, 'get_history'):
                continue

            (added, unchanged, deleted) = \
                    attr.impl.get_history(state, dict_, passive=passive)

            if added or deleted:
                return True
        return False

    @property
    def is_active(self):
        """True if this :class:`.Session` has an active transaction.
        
        This indicates if the :class:`.Session` is capable of emitting
        SQL, as from the :meth:`.Session.execute`, :meth:`.Session.query`,
        or :meth:`.Session.flush` methods.   If False, it indicates 
        that the innermost transaction has been rolled back, but enclosing
        :class:`.SessionTransaction` objects remain in the transactional
        stack, which also must be rolled back.
        
        This flag is generally only useful with a :class:`.Session`
        configured in its default mode of ``autocommit=False``.

        """

        return self.transaction and self.transaction.is_active

    identity_map = None
    """A mapping of object identities to objects themselves.
    
    Iterating through ``Session.identity_map.values()`` provides
    access to the full set of persistent objects (i.e., those 
    that have row identity) currently in the session.
    
    See also:
    
    :func:`.identity_key` - operations involving identity keys.
    
    """

    @property
    def _dirty_states(self):
        """The set of all persistent states considered dirty.

        This method returns all states that were modified including
        those that were possibly deleted.

        """
        return self.identity_map._dirty_states()

    @property
    def dirty(self):
        """The set of all persistent instances considered dirty.
        
        E.g.::
        
            some_mapped_object in session.dirty

        Instances are considered dirty when they were modified but not
        deleted.

        Note that this 'dirty' calculation is 'optimistic'; most
        attribute-setting or collection modification operations will
        mark an instance as 'dirty' and place it in this set, even if
        there is no net change to the attribute's value.  At flush
        time, the value of each attribute is compared to its
        previously saved value, and if there's no net change, no SQL
        operation will occur (this is a more expensive operation so
        it's only done at flush time).

        To check if an instance has actionable net changes to its
        attributes, use the :meth:`.Session.is_modified` method.

        """
        return util.IdentitySet(
            [state.obj()
             for state in self._dirty_states
             if state not in self._deleted])

    @property
    def deleted(self):
        "The set of all instances marked as 'deleted' within this ``Session``"

        return util.IdentitySet(self._deleted.values())

    @property
    def new(self):
        "The set of all instances marked as 'new' within this ``Session``."

        return util.IdentitySet(self._new.values())

_sessions = weakref.WeakValueDictionary()

def make_transient(instance):
    """Make the given instance 'transient'.

    This will remove its association with any 
    session and additionally will remove its "identity key",
    such that it's as though the object were newly constructed,
    except retaining its values.   It also resets the
    "deleted" flag on the state if this object
    had been explicitly deleted by its session.

    Attributes which were "expired" or deferred at the
    instance level are reverted to undefined, and 
    will not trigger any loads.

    """
    state = attributes.instance_state(instance)
    s = _state_session(state)
    if s:
        s._expunge_state(state)

    # remove expired state and 
    # deferred callables
    state.callables.clear()
    if state.key:
        del state.key
    if state.deleted:
        del state.deleted

def object_session(instance):
    """Return the ``Session`` to which instance belongs.

    If the instance is not a mapped instance, an error is raised.

    """

    try:
        return _state_session(attributes.instance_state(instance))
    except exc.NO_STATE:
        raise exc.UnmappedInstanceError(instance)


def _state_session(state):
    if state.session_id:
        try:
            return _sessions[state.session_id]
        except KeyError:
            pass
    return None

_new_sessionid = util.counter()
