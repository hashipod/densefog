import logging
from gevent import getcurrent
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql import and_, or_, not_
import sqlalchemy
from densefog.common import local

default_engine_settings = {
    'encoding': 'utf8',
    'pool_size': 50,
    # http://groups.google.com/group/sqlalchemy/browse_thread/thread/9412808e695168ea/c31f5c967c135be0
    'pool_recycle': 5,

    # to fix unicode problem in mysql + sqlalchemy
    # http://www.cnblogs.com/leether/archive/2011/10/12/2208038.html
    'connect_args': {'charset': 'utf8'},

    # echo
    'echo': False,
    'echo_pool': False,
}


def generate_engine_configuration(db, host='localhost', port=3306,
                                  user='root', passwd=''):
    if passwd:
        strategy = 'mysql+pymysql://%s:%s@%s:%s/%s' % (user, passwd, host, port, db)  # noqa
    else:
        strategy = 'mysql+pymysql://%s@%s:%s/%s' % (user, host, port, db)
    return strategy


class Database(object):
    log = logging.getLogger('database')

    def __init__(self, strategy, only=None, but=[], **params):
        settings = default_engine_settings.copy()

        if strategy.startswith('sqlite'):
            settings.pop('pool_size')
            settings.pop('connect_args')

        settings.update(params)

        self.engine = sqlalchemy.create_engine(strategy, **settings)
        self.strategy = strategy

        # use scoped_session,
        # so we can get same session in one request lifecycle.
        self.session = scoped_session(sessionmaker(bind=self.engine),
                                      scopefunc=getcurrent)

        # create meta
        self.meta = sqlalchemy.MetaData(self.engine)

        try:
            connection = self.engine.connect()
            connection.close()
        except Exception as ex:
            raise Exception('%s\n%s' % (strategy, ex))

        tables = only if only else self.engine.table_names()
        if but:
            tables = [t for t in tables if t not in but]
        self.meta.reflect(only=tables)
        self.base_model = declarative_base(bind=self.engine,
                                           metadata=self.meta)

        self.generate_all_table()

        # for convenience
        self.and_ = and_
        self.or_ = or_
        self.not_ = not_

    def __getitem__(self, key):
        if key in self.tables():
            return getattr(self, key)
        else:
            return {}[1]

    def close(self):
        return self.engine.dispose()

    def echo_on(self, flag=True):
        import sqlalchemy.log as echo_log
        self.engine.echo = flag
        echo_log.instance_logger(self.engine, flag)
        self.engine.pool.echo = flag
        echo_log.instance_logger(self.engine.pool, flag)

    def tables(self):
        return self.meta.tables.keys()

    def generate_all_table(self):
        for table_name in self.tables():
            table = self._get_table(table_name)
            try:
                setattr(self, table_name, table)
            except UnicodeEncodeError:
                pass

    def _get_table(self, table_name):
        table_schema = self.meta.tables[table_name]
        table = Table(self, table_schema)
        return table

    def execute(self, sql, **params):
        return Database._execute(self.session, sql, **params)

    @staticmethod
    def _execute(session, sql, as_dictionary=True, start=0, length=0,
                 is_count=False, raw=False):
        if isinstance(sql, (str, unicode)):
            result = session.execute(sql)
        else:
            # in a case of selection object, it's same anyway.
            result = session.execute(sql)

        if raw:
            return result

        # some sql like 'rename' does not return rows at all.
        if not result.returns_rows:
            return None

        # fetch some of rows or not
        if is_count:
            # this is a couting sql
            return result.fetchone()[0]
        elif length > 0:
            # fetch some rows.
            if hasattr(result.cursor, 'scroll'):
                if start >= result.rowcount:
                    return []
                result.cursor.scroll(start, mode='absolute')
                rows = result.fetchmany(length)
            else:
                rows = result.fetchall()
                rows = rows[start:start + length]
        else:
            # fetch all rows.
            rows = result.fetchall()

        if as_dictionary:
            return [dict(row.items()) for row in rows]
        else:
            return rows

    def drop_table(self, table):
        self.execute('drop table %s' % table)
        self.meta.reflect()
        delattr(self, table)

    def rename_table(self, _from, to):
        self.execute('rename table %s to %s' % (_from, to))
        delattr(self, _from)
        self.meta.reflect()
        table = self._get_table(to)
        setattr(self, to, table)
        return table


class Table(object):

    log = logging.getLogger('table')

    def __init__(self, database, schema):
        self.database = database
        self.session = database.session
        self.schema = schema
        self.engine = schema.bind
        if len(self.schema.primary_key) == 1:
            self.primary = self.schema.primary_key.columns.keys()[0]

        # for convenience
        self.and_ = and_
        self.or_ = or_
        self.not_ = not_

    def convert_type(self, column_type):
        converts = {
            sqlalchemy.CHAR: str,
            sqlalchemy.VARCHAR: str,
            sqlalchemy.DATE: str,
            sqlalchemy.DATETIME: str,
            sqlalchemy.INT: int,
            sqlalchemy.INTEGER: int,
            sqlalchemy.Integer: int,
            sqlalchemy.TEXT: str,
            sqlalchemy.NCHAR: str,
            sqlalchemy.NVARCHAR: str,
            sqlalchemy.BOOLEAN: bool,
            sqlalchemy.BigInteger: int,
            sqlalchemy.Binary: str,
            sqlalchemy.Boolean: bool,
            sqlalchemy.CHAR: str,
            sqlalchemy.CLOB: str,
            sqlalchemy.DATETIME: str,
            sqlalchemy.DECIMAL: float,
            sqlalchemy.Date: str,
            sqlalchemy.DateTime: str,
            sqlalchemy.Enum: int,
            sqlalchemy.FLOAT: float,
            sqlalchemy.Float: float,
            sqlalchemy.NUMERIC: str,
            sqlalchemy.SMALLINT: int,
            sqlalchemy.String: str,
            sqlalchemy.TEXT: str,
            sqlalchemy.TIME: str,
            sqlalchemy.TIMESTAMP: str,
            sqlalchemy.Time: str,
            sqlalchemy.Unicode: str,
            sqlalchemy.UnicodeText: str,
            sqlalchemy.types._Binary: str,
        }

        for type in converts:
            if isinstance(column_type, type):
                return converts[type]
        for type in converts:
            if issubclass(column_type.__class__, type):
                return converts[type]
        raise ValueError('could not convert %s' % column_type)

    @property
    def name(self):
        return self.schema.name

    @property
    def c(self):
        return self.schema.c

    @property
    def t(self):
        return self.schema

    # http://code.google.com/p/sqlalchemy-migrate/
    # seems useful
    def definition(self):
        from sqlalchemy.schema import CreateTable
        print(CreateTable(self.schema))

    @property
    # TODO: it's should not dic, it's should have keep suquence
    def fields(self):
        fields = {}
        for c in self.schema.columns:
            name = c.name
            primary = c.primary_key
            type = self.convert_type(c.type)
            nullable = c.nullable
            default = c.default
            fields[name] = (primary, type, nullable, default)
        return fields

    def make_where(self, wheresql):
        if isinstance(wheresql, dict):
            where = None
            for param, value in wheresql.items():
                clause = self.schema.columns[param] == value
                where = and_(where, clause) if where is not None else clause
            return where
        elif isinstance(wheresql, (str, unicode)):
            return wheresql
        elif hasattr(wheresql, '__call__'):
            return wheresql(self.t.c)
        elif isinstance(wheresql, sqlalchemy.sql.expression.ClauseElement):
            return wheresql
        else:
            raise Exception('WTF? where sql?')

    def make_primary_where(self, primary):
        return self.make_where({self.primary: primary})

    def select(self, where=None, fields=None, limit=None, order_by=None,
               **params):
        # in a case of BinaryExpression like table.c.id == 1
        # whould skip where check
        if where is not None:
            where = self.make_where(where)

        return self._select(where, fields, limit=limit, order_by=order_by,
                            **params)

    def _select(self, where, fields, limit=None, order_by=None, **params):
        if not fields:
            fields = self.fields.keys()

        columns = [c for c in self.schema.c if c.name in fields]
        selection = sqlalchemy.select(columns, where, from_obj=[self.schema])

        if order_by is not None:
            if isinstance(order_by, str):
                order_by = getattr(self.schema.c, order_by)
            elif hasattr(order_by, '__call__'):
                order_by = order_by(self.t.c)

            selection = selection.order_by(order_by)

        if limit:
            selection = selection.limit(limit)

        lock = params.pop('lock', None)
        if lock:
            selection = selection.with_for_update()

        rows = self.execute(selection, **params)

        return rows

    def get(self, primary, fields=None, as_dictionary=True, **params):
        where = self.make_primary_where(primary)
        rows = self._select(where, fields, as_dictionary=as_dictionary, **params)  # noqa
        if rows:
            return rows[0]
        else:
            return None

    def first(self, where=None, fields=None, order_by=None, **params):
        items = self.select(where=where, fields=fields, limit=1,
                            order_by=order_by, **params)
        return items[0] if items else None

    def inserts(self, items):
        """
        insert some rows. return the inserted row count.
        """
        items = [self.normalize_values(item) for item in items]

        sql = self.schema.insert(items)
        result = self.execute(sql, raw=True)

        if getattr(result, 'rowcount', None):
            return result.rowcount
        else:
            return None

    def insert(self, values={}, **kwargs):
        """
        insert one row. return the id.
        """
        values = values.copy()
        values.update(kwargs)

        sql = self.schema.insert(values)
        result = self.execute(sql, raw=True)

        if getattr(result, 'inserted_primary_key', None):
            return result.inserted_primary_key[0]
        else:
            return None

    def delete(self, primary):
        where = self.make_primary_where(primary)
        sql = self.schema.delete(where)
        self.execute(sql)

    def delete_any(self, where):
        where = self.make_where(where)
        sql = self.schema.delete(where)
        self.execute(sql)

    def delete_all(self):
        sql = self.schema.delete()
        self.execute(sql)

    def update(self, primary, values={}, **kwargs):
        values = values.copy()
        values.update(kwargs)
        values = self.normalize_values(values)
        where = self.make_primary_where(primary)
        sql = self.schema.update(where).values(values)
        ret = self.execute(sql, raw=True)
        return ret.rowcount

    def update_any(self, where, values={}, **kwargs):
        values = values.copy()
        values.update(kwargs)
        values = self.normalize_values(values)

        where = self.make_where(where)
        sql = self.schema.update(where).values(values)
        ret = self.execute(sql, raw=True)
        return ret.rowcount

    def execute(self, sql, **params):
        if local.in_trans_context():
            return Database._execute(self.database.session, sql, **params)
        else:
            return Database._execute(self.engine, sql, **params)

    def drop(self):
        self.database.drop_table(self.name)

    def rename(self, to):
        return self.database.rename_table(self.name, to)

    def normalize_values(self, values):
        for k in values:
            if isinstance(values[k], list):
                values[k] = ','.join(values[k])
        return values

    def count(self, where=None):
        if where is not None:
            where = self.make_where(where)
        sql = self.schema.count(where)
        return self.execute(sql, is_count=True)

    # extension
    def limitation(self, where=None, offset=0, limit=10, **params):
        count = self.count(where)
        if count > 0:
            return dict(
                items=self.select(where, start=offset, length=limit, **params),
                offset=offset,
                limit=limit,
                total=count
            )
        else:
            return dict(items=[], offset=0,
                        limit=limit, total=count)

    # extension
    def pagination(self, where=None, current_page=1, size=10, **params):
        count = self.count(where)
        if count > 0:
            current_page = current_page if current_page > 0 else 1
            if size == 0:
                size = count
            size = size if size > 0 else 10

            start = size * (current_page - 1)
            return dict(
                items=self.select(where, start=start, length=size, **params),
                current_page=current_page,
                last_page=(count - 1) / size + 1,
                size=size,
                total=count,
            )
        else:
            return dict(items=[], current_page=1, last_page=1,
                        size=size, total=count)
