import os
import sys

CONF = None


class config(object):

    def __init__(self, gevent):
        self.gevent = gevent

        self.app_name = None
        self.app_root = None
        self.app_port = None
        self.log_path = None

        self.debug = os.getenv('DEBUG') == 'True'

        self.db_host = os.getenv('DB_HOST')
        self.db_port = int(os.getenv('DB_PORT') or 3306)
        self.db_user = os.getenv('DB_USER')
        self.db_password = os.getenv('DB_PASSWORD')
        self.db_database = os.getenv('DB_DATABASE')

        self.redis_host = os.getenv('REDIS_HOST')
        self.redis_port = int(os.getenv('REDIS_PORT') or 6379)

    def apply(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

        app_root = kwargs.get('app_root', None)
        if app_root:
            sys.path.append(app_root)


def setup(gevent=True):
    global CONF

    if CONF is None:
        CONF = config(gevent)

    return CONF
