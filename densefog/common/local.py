from werkzeug.local import Local, release_local
from gevent import getcurrent
from densefog.common import utils

local = Local()


def _put_local(key, value):
    setattr(local, key, value)


def _get_local(key):
    return getattr(local, key, None)


def _del_local(key):
    try:
        delattr(local, key)
    except:
        pass


def start_context(tail=None):
    if not tail:
        tail = utils.generate_key(4)
    context_id = 'ctx-%s-%s' % (id(getcurrent()), tail)

    _put_local('context_id', context_id)


def get_context_id():
    return _get_local('context_id') or ""


def clear_context():
    release_local(local)


def in_trans_context():
    return _get_local('trans_context') is True


def enter_trans_context():
    _put_local('trans_context', True)


def exit_trans_context():
    _del_local('trans_context')


def in_lock_context():
    return _get_local('lock_context') is True


def enter_lock_context():
    _put_local('lock_context', True)


def exit_lock_context():
    _del_local('lock_context')
