import os
from densefog.common.rediscache import SimpleCache, cache_it_json


CACHE = cache_it_json


def get_cache_store(limit, expire):
    host = os.getenv('REDIS_HOST')
    port = os.getenv('REDIS_PORT')

    cache = SimpleCache(limit=limit,
                        expire=expire,
                        hashkeys=True,
                        host=host,
                        port=port,
                        db=1,
                        namespace='densefog')
    return cache


def setup():
    pass
