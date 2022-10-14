import sys
import time
import flask
import functools
from densefog.web import grand
from densefog import logger
from densefog.common import utils

from densefog.model.log import operation as operation_model


def mark_user_operation(resource_type, resource_ids_key):
    def marker(method):
        @functools.wraps(method)
        def wrap(*args, **kwargs):
            flask.request.operation_marker = True
            flask.request.operation_resource_type = resource_type
            flask.request.operation_resource_ids_key = resource_ids_key

            return method(*args, **kwargs)

        return wrap

    return marker


def log_user_operation(method):

    @functools.wraps(method)
    def wrap(*args, **kwargs):

        ret_code = 0
        ret_message = 'good job.'
        exc_info = None
        exc = None

        try:
            ret = method(*args, **kwargs)

        except grand.HandleError as e:
            ret_code = e.ret_code
            ret_message = e.message
            exc_info = sys.exc_info()
            exc = e

        except Exception as e:
            # normally you will not come to this clause,
            # because guard.guard_generic_failure handle generic Exceptions
            # and expose grand.HandleError to outer scope.
            ret_code = 5000
            ret_message = 'internal error..(from stat.log_user_operation)'
            exc_info = sys.exc_info()

        if (hasattr(flask.request, 'operation_marker') and
           flask.request.operation_marker):

            key = flask.request.key
            try:
                project_id = flask.request.project_id
            except:
                project_id = None

            resource_type = flask.request.operation_resource_type
            resource_ids_key = flask.request.operation_resource_ids_key

            resource_ids = []

            # first check if returned json has resource_ids_key,
            if not resource_ids:
                with utils.silent():
                    resource_ids = ret[resource_ids_key]

            # secondly check exception data has resource_ids_key
            if not resource_ids:
                with utils.silent():
                    resource_ids = exc.data[resource_ids_key]

            # thirdly check if request json has resource_ids_key.
            if not resource_ids:
                with utils.silent():
                    resource_ids = flask.request.params[resource_ids_key]

            if not isinstance(resource_ids, list):
                resource_ids = [resource_ids]

            operation_model.create(project_id, key,
                                   flask.request.action,
                                   flask.request.params,
                                   resource_type,
                                   resource_ids,
                                   ret_code,
                                   ret_message)

        if exc_info:
            typ, val, tb = exc_info[0], exc_info[1], exc_info[2]
            raise val.with_traceback(tb)

        else:
            return ret

    return wrap


def stat_user_access(method):
    @functools.wraps(method)
    def wrap(*args, **kwargs):
        start = int(time.time() * 1000)

        ret_code = 0
        exc_info = None

        try:
            ret = method(*args, **kwargs)
        except grand.HandleError as e:
            ret_code = e.ret_code
            exc_info = sys.exc_info()

        except Exception as e:
            # normally you will not come to this clause,
            # because guard.guard_generic_failure handle generic Exceptions
            # and expose grand.HandleError to outer scope.
            ret_code = 5000
            exc_info = sys.exc_info()

        try:
            action = flask.request.action
        except:
            action = None

        try:
            key = flask.request.key
        except:
            key = None

        try:
            project_id = flask.request.project_id
        except:
            project_id = None

        duration = int(time.time() * 1000) - start
        client_ip = flask.request.environ.get('HTTP_X_REAL_IP',
                                              flask.request.remote_addr)

        message = """{client_ip} {project_id} {key} {action} {duration}ms {rescode}""".format(  # noqa
                client_ip=client_ip,
                project_id=project_id,
                key=key,
                action=action,
                duration=duration,
                rescode=ret_code)

        logger.ACCESS.info(message)

        if exc_info:
            typ, val, tb = exc_info[0], exc_info[1], exc_info[2]
            raise val.with_traceback(tb)

        else:
            return ret

    return wrap
