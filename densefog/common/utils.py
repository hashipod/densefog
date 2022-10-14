import sys
import traceback
import datetime
import uuid
import re
import shortuuid
from contextlib import contextmanager
import functools


def import_class(path):
    module_path = '.'.join(path.split('.')[:-1])
    __import__(module_path)
    module = sys.modules[module_path]
    class_name = path.split('.')[-1]
    return getattr(module, class_name)


def generate_uuid():
    return str(uuid.uuid4())


def generate_key(length=10):
    return shortuuid.ShortUUID().random(length=length)


def encode_uuid(u):
    return shortuuid.encode(uuid.UUID(u))


def decode_uuid(s):
    return str(shortuuid.decode(s))


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)


def extract(data, fields):
    result = {}
    for field in fields:
        if isinstance(field, tuple):
            field, opts = field[0], field[1]

            if 'convert' in opts:
                result[field] = opts['convert'](data)
            if 'rename' in opts:
                result[field] = data[opts['rename']]
        else:
            result[field] = data[field]
    return result


def extract_list(items, fields):
    for i, item in enumerate(items):
        items[i] = extract(item, fields)
    return items


ISO8601_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def format_iso8601(date):
    return datetime.datetime.strftime(date,
                                      ISO8601_FORMAT)


def parse_iso8601(date_str):
    return datetime.datetime.strptime(date_str,
                                      ISO8601_FORMAT)


def seconds_later(s):
    return datetime.datetime.utcnow() + datetime.timedelta(seconds=s)


def snake_case(func_name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', func_name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def camel_case(func_name):
    return ''.join(x for x in func_name.title() if not x.isspace())


p_r1 = re.compile(r'[0-9a-zA-Z~!@#$%^&*()_+]{8,}')     # at lease 8 charactors
p_r2 = re.compile(r'.*[0-9]+.*')          # at lease one number
p_r3 = re.compile(r'.*[a-z]+.*')       # at lease one lowercase letter
p_r4 = re.compile(r'.*[A-Z]+.*')       # at lease one uppercase letter


def strong_password(p):
    if p_r1.match(p) and p_r2.match(p) and p_r3.match(p) and p_r4.match(p):
        return True
    return False


def hide_secret(d):
    d = d or {}
    ret = {}
    for k, v in d.items():
        try:
            if 'password' in k.lower():
                v = '*' * 8
            if 'user_data' in k.lower():
                v = 'user_data'
            if type(v) is dict:
                ret[k] = hide_secret(v)
            else:
                ret[k] = v
        except:
            pass
    return ret


n_r1 = re.compile(r'^[0-9a-zA-Z_\-]+$')


def simple_name(n):
    if not n:
        return True

    if n_r1.match(n):
        return True
    return False


class MockObject(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)

    def __getitem__(self, key):
        return getattr(self, key)


def footprint(logger):

    def outer(method):
        method_name = '.%s() ' % method.__name__

        @functools.wraps(method)
        def inner(*args, **kwargs):
            try:
                logger.info(method_name + 'start.')
                ret = method(*args, **kwargs)
            except:
                logger.error(method_name + 'fail!')
                stack = traceback.format_exc()
                logger.stacktrace(stack)
                raise
            else:
                logger.info(method_name + 'OK.')
                return ret

        return inner

    return outer


@contextmanager
def silent(callback=None):
    try:
        yield
    except Exception as e:
        if callback:
            callback(e)
        pass


@contextmanager
def defer_reraise():
    exc_info = sys.exc_info()
    try:
        yield
    finally:
        if exc_info:
            typ, val, tb = exc_info[0], exc_info[1], exc_info[2]
            raise val.with_traceback(tb)
