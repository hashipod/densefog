class BaseIaasException(Exception):
    def __init__(self, message=None):
        self.message = 'error happened.'

    def __str__(self):
        return self.message


class ClientRequestException(BaseIaasException):
    def __init__(self, message=None):
        if message is None:
            message = 'request input is illegal.'

        self.message = str(message)


##################################################################
#
#  ClientRequestException ==>  Request & Resource Exception Family
#
##################################################################

class BaseResourceException(ClientRequestException):
    def __init__(self, resource_id):
        self.resource_id = resource_id
        self.message = 'Resource exception happened'


class ResourceNotFound(BaseResourceException):
    def __init__(self, resource_id):
        BaseResourceException.__init__(self, resource_id)
        self.message = 'Resource (%s) is not found' % str(resource_id)


class ResourceNotBelongsToProject(BaseResourceException):
    def __init__(self, resource_id):
        BaseResourceException.__init__(self, resource_id)
        self.message = 'You have no permission on this resource (%s)' % str(resource_id)  # noqa


class ResourceActionForbiden(BaseResourceException):
    def __init__(self, resource_id):
        BaseResourceException.__init__(self, resource_id)
        self.message = 'Resource (%s) action is forbiden.' % str(resource_id)  # noqa


class ResourceActionUnsupported(BaseResourceException):
    def __init__(self, resource_id):
        BaseResourceException.__init__(self, resource_id)
        self.message = 'Resource (%s) action is supported.' % str(resource_id)  # noqa


class InvalidRequestParameter(BaseIaasException):
    def __init__(self, message=None):
        self.message = message or 'request parameter is invalid'


class ValidationError(InvalidRequestParameter):
    def __init__(self, message=None):
        self.message = message or 'can not validate request json'


##################################################################
#
#  ClientRequestException ==>  Action Forbiden Exception Family
#
##################################################################


class ResourceIsBusy(ResourceActionForbiden):
    def __init__(self, resource_id):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not do action, because resource (%s) is busy now.'
                         % str(resource_id))  # noqa


class ResourceIsDeleted(ResourceActionForbiden):
    def __init__(self, resource_id):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not do action, because resource (%s) is deleted.'
                         % str(resource_id))  # noqa


class ResourceIsInError(ResourceActionForbiden):
    def __init__(self, resource_id):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not do action, because resource (%s) is in error.'
                         % str(resource_id))  # noqa


##################################################################
#
#  Server Side Error.
#
##################################################################

class ServerInternalError(BaseIaasException):
    def __init__(self, message=None):
        if message is None:
            message = 'we have a server problem.'

        self.message = str(message)


##################################################################
#
#  Server Side Error ==> Provider Error Family
#
##################################################################

class IaasProviderActionError(ServerInternalError):
    """
    an iaas provider action failed.
    generic error. you could subclass it to support more detailed
    exception.

    we should save openstack stacktrace here, or else we will lose
    openstack stacktrace.
    """
    def __init__(self, exception, stacktrace, message=None):
        self.exception = exception
        self.stacktrace = stacktrace
        self.message = message

    def __str__(self):
        return "%s:\n%s" % (self.__class__.__name__, self.stacktrace)


##################################################################
#
#  Server Side Error ==> Waiter Error Family
#
##################################################################

class BaseWaiterError(ServerInternalError):
    def __init__(self, exception, stacktrace):
        self.exception = exception
        self.stacktrace = stacktrace

    def __str__(self):
        return "%s:\n%s" % (self.__class__.__name__, self.stacktrace)


class WaitObjectNotFound(BaseWaiterError):
    pass


class WaitObjectInterrupt(BaseWaiterError):
    def __init__(self, message=None):
        if message is None:
            message = 'wait object interrupt error.'

        self.message = str(message)

    def __str__(self):
        return self.message


class WaitObjectTimeout(BaseWaiterError):
    def __init__(self, message=None):
        if message is None:
            message = 'wait object timeout error.'

        self.message = str(message)

    def __str__(self):
        return self.message


##################################################################
#
#  Server Side Error ==> Job Error Family
#
##################################################################

class BaseJobException(ServerInternalError):
    def __init__(self):
        self.message = 'Job execution error.'


class JobNotFound(BaseJobException):
    def __init__(self, job_id):
        self.job_id = job_id
        self.message = 'Job (%s) is not found' % job_id


##################################################################
#
#  Server Side Error ==> DB Error Family
#
##################################################################

class DBLockTimeoutError(ServerInternalError):
    def __init__(self, message=None):
        if message is None:
            message = 'we have a db problem.'

        self.message = message
