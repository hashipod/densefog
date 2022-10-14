import sys
from gevent import monkey
from densefog import config
from densefog import db
from densefog import cache

GEVENT = False


def init():
    if config.CONF.db_host:
        db.setup()

    if config.CONF.redis_host:
        cache.setup()

    if config.CONF.gevent:
        global GEVENT
        GEVENT = True

        # flask's auto loader
        # http://flask.pocoo.org/snippets/34/
        monkey.patch_all()
