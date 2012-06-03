# ext/orderinglist.py
# Copyright (C) 2005-2012 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""A custom list that manages index/position information for its children.

:author: Jason Kirtland

``orderinglist`` is a helper for mutable ordered relationships.  It will intercept
list operations performed on a relationship collection and automatically
synchronize changes in list position with an attribute on the related objects.
(See :ref:`advdatamapping_entitycollections` for more information on the general pattern.)

Example: Two tables that store slides in a presentation.  Each slide
has a number of bullet points, displayed in order by the 'position'
column on the bullets table.  These bullets can be inserted and re-ordered
by your end users, and you need to update the 'position' column of all
affected rows when changes are made.

.. sourcecode:: python+sql

    slides_table = Table('Slides', metadata,
                         Column('id', Integer, primary_key=True),
                         Column('name', String))

    bullets_table = Table('Bullets', metadata,
                          Column('id', Integer, primary_key=True),
                          Column('slide_id', Integer, ForeignKey('Slides.id')),
                          Column('position', Integer),
                          Column('text', String))

     class Slide(object):
         pass
     class Bullet(object):
         pass

     mapper(Slide, slides_table, properties={
           'bullets': relationship(Bullet, order_by=[bullets_table.c.position])
     })
     mapper(Bullet, bullets_table)

The standard relationship mapping will produce a list-like attribute on each Slide
containing all related Bullets, but coping with changes in ordering is totally
your responsibility.  If you insert a Bullet into that list, there is no
magic- it won't have a position attribute unless you assign it it one, and
you'll need to manually renumber all the subsequent Bullets in the list to
accommodate the insert.

An ``orderinglist`` can automate this and manage the 'position' attribute on all
related bullets for you.

.. sourcecode:: python+sql

    mapper(Slide, slides_table, properties={
           'bullets': relationship(Bullet,
                               collection_class=ordering_list('position'),
                               order_by=[bullets_table.c.position])
    })
    mapper(Bullet, bullets_table)

    s = Slide()
    s.bullets.append(Bullet())
    s.bullets.append(Bullet())
    s.bullets[1].position
    >>> 1
    s.bullets.insert(1, Bullet())
    s.bullets[2].position
    >>> 2

Use the ``ordering_list`` function to set up the ``collection_class`` on relationships
(as in the mapper example above).  This implementation depends on the list
starting in the proper order, so be SURE to put an order_by on your relationship.

.. warning:: 

  ``ordering_list`` only provides limited functionality when a primary
  key column or unique column is the target of the sort.  Since changing the order of 
  entries often means that two rows must trade values, this is not possible when 
  the value is constrained by a primary key or unique constraint, since one of the rows
  would temporarily have to point to a third available value so that the other row
  could take its old value.   ``ordering_list`` doesn't do any of this for you, 
  nor does SQLAlchemy itself.

``ordering_list`` takes the name of the related object's ordering attribute as
an argument.  By default, the zero-based integer index of the object's
position in the ``ordering_list`` is synchronized with the ordering attribute:
index 0 will get position 0, index 1 position 1, etc.  To start numbering at 1
or some other integer, provide ``count_from=1``.

Ordering values are not limited to incrementing integers.  Almost any scheme
can implemented by supplying a custom ``ordering_func`` that maps a Python list
index to any value you require.




"""
from sqlalchemy.orm.collections import collection
from sqlalchemy import util

__all__ = [ 'ordering_list' ]


def ordering_list(attr, count_from=None, **kw):
    """Prepares an OrderingList factory for use in mapper definitions.

    Returns an object suitable for use as an argument to a Mapper relationship's
    ``collection_class`` option.  Arguments are:

    attr
      Name of the mapped attribute to use for storage and retrieval of
      ordering information

    count_from (optional)
      Set up an integer-based ordering, starting at ``count_from``.  For
      example, ``ordering_list('pos', count_from=1)`` would create a 1-based
      list in SQL, storing the value in the 'pos' column.  Ignored if
      ``ordering_func`` is supplied.

    Passes along any keyword arguments to ``OrderingList`` constructor.
    """

    kw = _unsugar_count_from(count_from=count_from, **kw)
    return lambda: OrderingList(attr, **kw)

# Ordering utility functions
def count_from_0(index, collection):
    """Numbering function: consecutive integers starting at 0."""

    return index

def count_from_1(index, collection):
    """Numbering function: consecutive integers starting at 1."""

    return index + 1

def count_from_n_factory(start):
    """Numbering function: consecutive integers starting at arbitrary start."""

    def f(index, collection):
        return index + start
    try:
        f.__name__ = 'count_from_%i' % start
    except TypeError:
        pass
    return f

def _unsugar_count_from(**kw):
    """Builds counting functions from keyword arguments.

    Keyword argument filter, prepares a simple ``ordering_func`` from a
    ``count_from`` argument, otherwise passes ``ordering_func`` on unchanged.
    """

    count_from = kw.pop('count_from', None)
    if kw.get('ordering_func', None) is None and count_from is not None:
        if count_from == 0:
            kw['ordering_func'] = count_from_0
        elif count_from == 1:
            kw['ordering_func'] = count_from_1
        else:
            kw['ordering_func'] = count_from_n_factory(count_from)
    return kw

class OrderingList(list):
    """A custom list that manages position information for its children.

    See the module and __init__ documentation for more details.  The
    ``ordering_list`` factory function is used to configure ``OrderingList``
    collections in ``mapper`` relationship definitions.

    """

    def __init__(self, ordering_attr=None, ordering_func=None,
                 reorder_on_append=False):
        """A custom list that manages position information for its children.

        ``OrderingList`` is a ``collection_class`` list implementation that
        syncs position in a Python list with a position attribute on the
        mapped objects.

        This implementation relies on the list starting in the proper order,
        so be **sure** to put an ``order_by`` on your relationship.

        :param ordering_attr: 
          Name of the attribute that stores the object's order in the
          relationship.

        :param ordering_func: Optional.  A function that maps the position in the Python list to a
          value to store in the ``ordering_attr``.  Values returned are
          usually (but need not be!) integers.

          An ``ordering_func`` is called with two positional parameters: the
          index of the element in the list, and the list itself.

          If omitted, Python list indexes are used for the attribute values.
          Two basic pre-built numbering functions are provided in this module:
          ``count_from_0`` and ``count_from_1``.  For more exotic examples
          like stepped numbering, alphabetical and Fibonacci numbering, see
          the unit tests.

        :param reorder_on_append: 
          Default False.  When appending an object with an existing (non-None)
          ordering value, that value will be left untouched unless
          ``reorder_on_append`` is true.  This is an optimization to avoid a
          variety of dangerous unexpected database writes.

          SQLAlchemy will add instances to the list via append() when your
          object loads.  If for some reason the result set from the database
          skips a step in the ordering (say, row '1' is missing but you get
          '2', '3', and '4'), reorder_on_append=True would immediately
          renumber the items to '1', '2', '3'.  If you have multiple sessions
          making changes, any of whom happen to load this collection even in
          passing, all of the sessions would try to "clean up" the numbering
          in their commits, possibly causing all but one to fail with a
          concurrent modification error.  Spooky action at a distance.

          Recommend leaving this with the default of False, and just call
          ``reorder()`` if you're doing ``append()`` operations with
          previously ordered instances or when doing some housekeeping after
          manual sql operations.

        """
        self.ordering_attr = ordering_attr
        if ordering_func is None:
            ordering_func = count_from_0
        self.ordering_func = ordering_func
        self.reorder_on_append = reorder_on_append

    # More complex serialization schemes (multi column, e.g.) are possible by
    # subclassing and reimplementing these two methods.
    def _get_order_value(self, entity):
        return getattr(entity, self.ordering_attr)

    def _set_order_value(self, entity, value):
        setattr(entity, self.ordering_attr, value)

    def reorder(self):
        """Synchronize ordering for the entire collection.

        Sweeps through the list and ensures that each object has accurate
        ordering information set.

        """
        for index, entity in enumerate(self):
            self._order_entity(index, entity, True)

    # As of 0.5, _reorder is no longer semi-private
    _reorder = reorder

    def _order_entity(self, index, entity, reorder=True):
        have = self._get_order_value(entity)

        # Don't disturb existing ordering if reorder is False
        if have is not None and not reorder:
            return

        should_be = self.ordering_func(index, self)
        if have != should_be:
            self._set_order_value(entity, should_be)

    def append(self, entity):
        super(OrderingList, self).append(entity)
        self._order_entity(len(self) - 1, entity, self.reorder_on_append)

    def _raw_append(self, entity):
        """Append without any ordering behavior."""

        super(OrderingList, self).append(entity)
    _raw_append = collection.adds(1)(_raw_append)

    def insert(self, index, entity):
        super(OrderingList, self).insert(index, entity)
        self._reorder()

    def remove(self, entity):
        super(OrderingList, self).remove(entity)
        self._reorder()

    def pop(self, index=-1):
        entity = super(OrderingList, self).pop(index)
        self._reorder()
        return entity

    def __setitem__(self, index, entity):
        if isinstance(index, slice):
            step = index.step or 1
            start = index.start or 0
            if start < 0:
                start += len(self)
            stop = index.stop or len(self)
            if stop < 0:
                stop += len(self)

            for i in xrange(start, stop, step):
                self.__setitem__(i, entity[i])
        else:
            self._order_entity(index, entity, True)
            super(OrderingList, self).__setitem__(index, entity)

    def __delitem__(self, index):
        super(OrderingList, self).__delitem__(index)
        self._reorder()

    # Py2K
    def __setslice__(self, start, end, values):
        super(OrderingList, self).__setslice__(start, end, values)
        self._reorder()

    def __delslice__(self, start, end):
        super(OrderingList, self).__delslice__(start, end)
        self._reorder()
    # end Py2K

    def __reduce__(self):
        return _reconstitute, (self.__class__, self.__dict__, list(self))

    for func_name, func in locals().items():
        if (util.callable(func) and func.func_name == func_name and
            not func.__doc__ and hasattr(list, func_name)):
            func.__doc__ = getattr(list, func_name).__doc__
    del func_name, func

def _reconstitute(cls, dict_, items):
    """ Reconstitute an ``OrderingList``.

    This is the adjoint to ``OrderingList.__reduce__()``.  It is used for
    unpickling ``OrderingList``\\s

    """
    obj = cls.__new__(cls)
    obj.__dict__.update(dict_)
    list.extend(obj, items)
    return obj
