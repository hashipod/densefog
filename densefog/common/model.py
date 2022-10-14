import logging
from sqlalchemy.orm import mapper
from sqlalchemy import func
from sqlalchemy.sql import and_, or_, not_


class BaseOrm(object):
    mapper = None


class ModelError(Exception):

    def __str__(self):
        # all sub-classes should set self._message in their initializers
        return self._message


class Model(object):

    deletable = True
    log = logging.getLogger('model')

    func = func

    def __init__(self, **attrs):
        self.__dict__.update(attrs)

    def __getitem__(self, k):
        return self.__dict__[k]

    def __setitem__(self, k, v):
        self.__dict__[k] = v

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)

    @staticmethod
    def not_(*args):
        return not_(*args)

    @staticmethod
    def or_(*args):
        return or_(*args)

    @staticmethod
    def and_(*args):
        return and_(*args)

    @classmethod
    def Orm(cls):
        if not hasattr(cls, '_obj'):

            Orm = type('%sOrm' % cls.__name__, (BaseOrm,), {})
            Orm.mapper = mapper(Orm, cls.db().t)
            setattr(cls, '_obj', Orm)

        return cls._obj

    @classmethod
    def db(cls):
        return cls.table

    @classmethod
    def _where_with_deleted(cls, where, flag=1):
        if where is None:
            def where(t):
                return ''

        def wrap_where(t):
            return cls.db().and_(where(t), t.deleted == flag)
        return wrap_where

    @classmethod
    def count(cls, where=None):
        if cls.deletable:
            return cls.db().count(where)
        else:
            return cls.db().count(cls._where_with_deleted(where, 0))

    @classmethod
    def first(cls, where=None, fields=None, order_by=None):
        items = cls.list(where=where, fields=fields, order_by=order_by,
                         limit=1)
        if items:
            return items[0]
        else:
            return None

    @classmethod
    def first_as_model(cls, where=None, fields=None, order_by=None):
        item = cls.first(where, fields, order_by)
        if item:
            return cls(**item)
        else:
            return None

    @classmethod
    def list(cls, where=None, fields=None, limit=None, order_by=None):
        if cls.deletable:
            return cls.db().select(where, fields,
                                   limit=limit, order_by=order_by)
        else:
            return cls.db().select(cls._where_with_deleted(where, 0), fields,
                                   limit=limit, order_by=order_by)

    @classmethod
    def list_as_model(cls, where=None, fields=None, limit=None, order_by=None):
        items = cls.list(where, fields, limit, order_by)
        return [cls(**item) for item in items]

    select = list

    @classmethod
    def get(cls, id, include_deleted=False, lock=None):
        item = cls.db().get(id, lock=lock)

        if item and not cls.deletable and \
           not include_deleted and item['deleted'] == 1:
            return None
        else:
            return item

    @classmethod
    def get_as_model(cls, id, include_deleted=False, lock=None):
        item = cls.get(id, include_deleted, lock=lock)
        if item is None:
            return None
        else:
            return cls(**item)

    @classmethod
    def update_any(cls, where, **kwargs):
        if cls.deletable:
            return cls.db().update_any(where, **kwargs)
        else:
            return cls.db().update_any(cls._where_with_deleted(where, 0),
                                       **kwargs)

    @classmethod
    def update(cls, id, **kwargs):
        if not cls.deletable:
            cls.get(id)

        cls.db().update(id, **kwargs)

    @classmethod
    def delete_any(cls, where):
        if cls.deletable:
            cls.db().delete_any(where)
        else:
            cls.db().update(where, deleted=1)

    @classmethod
    def delete(cls, id):
        if cls.deletable:
            cls.db().delete(id)
        else:
            cls.db().update(id, deleted=1)

    @classmethod
    def insert(cls, **kwargs):
        if not cls.deletable:
            kwargs.setdefault('deleted', 0)

        return cls.db().insert(**kwargs)

    @classmethod
    def deleted(cls):
        if cls.deletable:
            raise Exception('could not find any delete item.')
        else:
            return cls.db().select(cls._where_with_deleted(None, 1))

    @classmethod
    def limitation(cls, where=None, fields=None,
                   order_by=None, offset=0, limit=10):
        if not cls.deletable:
            where = cls._where_with_deleted(where, 0)

        return cls.db().limitation(where, offset=offset,
                                   limit=limit,
                                   fields=fields, order_by=order_by)

    @classmethod
    def limitation_as_model(cls, where=None, fields=None,
                            order_by=None, offset=1, limit=10):
        page = cls.limitation(where, fields, order_by, offset, limit)
        page['items'] = [cls(**item) for item in page['items']]
        return page

    @classmethod
    def pagination(cls, where=None, fields=None,
                   order_by=None, current_page=1, size=10):
        if not cls.deletable:
            where = cls._where_with_deleted(where, 0)

        return cls.db().pagination(where, current_page=current_page,
                                   size=size,
                                   fields=fields, order_by=order_by)

    @classmethod
    def pagination_as_model(cls, where=None, fields=None,
                            order_by=None, current_page=1, size=10):
        page = cls.pagination(where, fields, order_by, current_page, size)
        page['items'] = [cls(**item) for item in page['items']]
        return page
