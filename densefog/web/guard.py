import traceback
import functools
from densefog import config
from densefog import logger
from densefog.web import grand

from densefog.error_code import *

from densefog import error


def guard_provider_failure(method):
    """
    response an error when openstack provider report an error.

    NOTICE: it only check IaasProviderActionError, which is throwed by
    model api explicitly.
    for those apis who throws ActionsPartialSuccessError, and containing
    IaasProviderActionError, is handled by guard_partial_success.
    mostly, model apis deal with plural-actions, which means they always
    throw ActionsPartialSuccessError.
    but for some model apis, they DID throw IaasProviderActionError.
    such as eip.associate, image.create, network.create.  etc.
    """
    @functools.wraps(method)
    def guard(*args, **kwargs):
        try:
            return method(*args, **kwargs)

        except error.IaasProviderActionError as e:
            logger.stacktrace(e.stacktrace)
            logger.stacktrace(e.exception)
            logger.stacktrace(e.message)

            data = {}
            if config.CONF.debug:
                data['exceptionStr'] = str(e)

            raise grand.HandleError('Action failed.op', ErrCodeProviderError, data=data)   # noqa

    return guard


def guard_params_failure(method):
    """
    response an error when json schema validation error.
    """
    @functools.wraps(method)
    def guard(*args, **kwargs):
        try:
            return method(*args, **kwargs)

        except error.ValidationError as e:
            stack = traceback.format_exc()
            logger.stacktrace(stack)

            data = {}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            msg = 'Illegal request format, %s.' % e.message
            raise grand.HandleError(msg, ErrCodeRequestParamValidationError, data={})

        except error.InvalidRequestParameter as e:
            stack = traceback.format_exc()
            logger.stacktrace(stack)

            data = {}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise grand.HandleError(str(e), ErrCodeRequestParamUnkownAction, data=data)

    return guard


def guard_resource_failure(method):
    """
    response an error when resource related exceptions happend.
    like InstanceCanNotStart, InstanceCanNotStop, InstanceCanNotRestart etc.
    but here, we just deal with top level resource exceptions.
    """

    @functools.wraps(method)
    def guard(*args, **kwargs):
        try:
            return method(*args, **kwargs)

        except error.ResourceNotFound as e:
            stack = traceback.format_exc()
            logger.stacktrace(stack)

            data = {'resourceId': e.resource_id}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise grand.HandleError(str(e), ErrCodeResourceNotFound, data=data)

        except error.ResourceNotBelongsToProject as e:
            stack = traceback.format_exc()
            logger.stacktrace(stack)

            data = {'resourceId': e.resource_id}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise grand.HandleError(str(e), ErrCodeResourceNotBelongsToProject, data=data)

        except error.ResourceActionForbiden as e:
            stack = traceback.format_exc()
            logger.stacktrace(stack)

            data = {'resourceId': e.resource_id}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise grand.HandleError(str(e), ErrCodeResourceActionForbiden, data=data)

        except error.ResourceActionUnsupported as e:
            stack = traceback.format_exc()
            logger.stacktrace(stack)

            data = {'resourceId': e.resource_id}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise grand.HandleError(str(e), ErrCodeResourceActionUnsupported, data=data)

        except error.ResourceIsBusy as e:
            stack = traceback.format_exc()
            logger.stacktrace(stack)

            data = {'resourceId': e.resource_id}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise grand.HandleError(str(e), ErrCodeResourceActionForbiden, data=data)

    return guard


def guard_generic_failure(method):
    """
    response an error when api method throw some generic error.
    this guard should be applied to every api method, for any generic error.

    the outer scope grand.handle should only need to deal grand.HandleError

    the lower scope guard_**** method deal with specific errors. like
    ResourceQuotaNotEnough, IaasProviderActionError etc.
    they are often applied to specific methods.

    any other errors should be deal here..
    like InstanceCanNotStart, InstanceCanNotStop, InstanceCanNotRestart etc.
    it's applied to every method.
    THIS SHOULD BE APPLIED AS THE LAST FENCE.
    """

    @functools.wraps(method)
    def guard(*args, **kwargs):
        try:
            return method(*args, **kwargs)

        except grand.HandleError as e:
            # if lower model or api method have dealt with the exception
            # and throws out HandleError, use it directly.

            # do not log handleError here. lower model or api method
            # should log the error before throw it out.

            # logger.error(traceback.format_exc())

            raise

        except Exception as e:
            stack = traceback.format_exc()
            logger.stacktrace(stack)

            data = {}

            if config.CONF.debug:
                data = {'exceptionStr': stack}

            raise grand.HandleError(str(e), ErrCodeServerError, data=data)

    return guard
