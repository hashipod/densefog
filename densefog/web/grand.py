import time
import traceback
import functools
from functools import update_wrapper
from flask import request, make_response, current_app
from datetime import timedelta
from densefog import config
from densefog import logger
from densefog.common import jsonable
from densefog.common import local

from densefog.error_code import *


class HandleError(Exception):

    def __init__(self, message, ret_code=None, data=None):
        self.message = message
        self.ret_code = ret_code
        self.data = data

    def __unicode__(self):
        return unicode(self.message)

    def __str__(self):
        return str(self.message)

    def __repr__(self):
        return repr(self.message)


def handle(method):

    @functools.wraps(method)
    def wrap(*args, **kwargs):
        local.start_context()
        logger.info('Begin handle request.')

        start = time.time()

        try:
            data = method(*args, **kwargs)
            ret_code = 0
            message = None

        except HandleError as ex:
            logger.error('Getting HandleError on grand.handle.')

            data = ex.data or {}
            ret_code = ex.ret_code
            message = ex.message

            data['exceptionTag'] = local.get_context_id()

        except Exception as ex:
            # normally we should not come to here. lower api should
            # handle every exception.
            stack = traceback.format_exc()
            logger.stacktrace(stack)

            logger.error('Getting Exception on grand.handle.')

            data = {}
            if config.CONF.debug:
                data['exceptionStr'] = stack
            data['exceptionTag'] = local.get_context_id()

            ret_code = ErrCodeServerError
            message = 'An error occurred while processing your request.'

        ret = {
            'data': data,
            'retCode': ret_code,
            'message': message
        }

        try:
            if 'pretty' in request.args:
                json_data = jsonable.dumps(ret,
                                           indent=4,
                                           sort_keys=True,
                                           str=True)
            else:
                json_data = jsonable.dumps(ret, str=True)

        except Exception as ex:
            stack = traceback.format_exc()
            logger.stacktrace(stack)

            logger.error('jsonable.dumps catch exception: %s' % ex)

            data = {}
            if config.CONF.debug:
                data['exceptionStr'] = stack
            data['exceptionTag'] = local.get_context_id()

            json_data = jsonable.dumps({
                'data': data,
                'retCode': 5000,
                'message': message
            }, str=True)

        # we always response 200 HTTP code... we use different retCode.
        status_code = 200

        response = make_response(json_data, status_code)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'

        cost = time.time() - start
        message = '%s\t%s\t%s\t%s\t%s\t%s' % (request.remote_addr,
                                              ret_code,
                                              status_code,
                                              request.method,
                                              request.path,
                                              cost)
        logger.info(message)

        logger.info('End handle request. end context.')
        local.clear_context()

        return response
    return wrap


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers
            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            h['Access-Control-Allow-Credentials'] = 'true'
            h['Access-Control-Allow-Headers'] = \
                "Origin, X-Requested-With, Content-Type, Accept, Authorization"
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator
