import json
import datetime
from . import utils


def raise_type_error(obj, ex):
    FORMAT = 'Object of type %s with value of %s is not JSON serializable. %s'
    raise TypeError(FORMAT % (type(obj), repr(obj), str(ex)))


class ComplexEncoder(json.JSONEncoder):

    def default(self, obj):
        if hasattr(obj, 'jsonable'):
            return obj.jsonable()
        elif isinstance(obj, datetime.datetime):
            return utils.format_iso8601(obj)
        elif hasattr(obj, '__iter__'):
            return list(obj)
        else:
            try:
                return json.JSONEncoder.default(self, obj)
            except Exception as ex:
                if isinstance(obj, object) and hasattr(obj, '__dict__'):
                    return obj.__dict__
                else:
                    raise_type_error(obj, ex)


def dumps(obj, str=False, **kwargs):
    """str=False means the json it dumps could be unicoded."""
    return json.dumps(obj, cls=ComplexEncoder, ensure_ascii=str, **kwargs)


def loads(spec):
    return json.loads(spec)
