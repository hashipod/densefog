import sys
import traceback
import time
import functools
from contextlib import contextmanager
from densefog.common import model
from densefog.common import local

from densefog import error

from densefog import logger
logger = logger.getChild(__file__)


class BaseModel(model.Model):
    pass


def _acquire_lock(method):
    @functools.wraps(method)
    def wrap(*args, **kwargs):
        if local.in_lock_context():
            kwargs['lock'] = True
            logger.info('need acquire lock, args: %s.' % (args, ))
        return method(*args, **kwargs)
    return wrap


class LockableModel(BaseModel):
    @classmethod
    @_acquire_lock
    def get_as_model(cls, *args, **kwargs):
        return super(LockableModel, cls).get_as_model(*args, **kwargs)


class StatusModel(LockableModel):
    def __init__(self, *args, **kwargs):
        super(StatusModel, self).__init__(*args, **kwargs)
        assert hasattr(self, 'status'), ('StatusModel '
                                         'must have status field')

    def must_not_busy(self):
        if self.is_busy():
            raise error.ResourceIsBusy(self['id'])
        return True

    def must_not_deleted(self):
        if self.is_deleted():
            raise error.ResourceIsDeleted(self['id'])
        return True

    def must_not_error(self):
        if self.is_error():
            raise error.ResourceIsInError(self['id'])
        return True

    def must_be_available(self):
        self.must_not_busy()
        self.must_not_deleted()
        self.must_not_error()

    def is_busy(self):
        return self['status'].endswith('ing')

    def is_deleted(self):
        return self['status'] in ['deleted', 'ceased']

    def is_error(self):
        return self['status'] in ['error']


class ProjectModel(LockableModel):
    def __init__(self, *args, **kwargs):
        super(ProjectModel, self).__init__(*args, **kwargs)
        assert hasattr(self, 'project_id'), ('ProjectModel '
                                             'must have project field')

    def must_belongs_project(self, project_id):
        if self['project_id'] != project_id:
            raise error.ResourceNotBelongsToProject(self['id'])
        return True


class ResourceModel(StatusModel, ProjectModel):
    pass


@contextmanager
def lock_for_update():
    logger.info('enter lock context.')

    local.enter_lock_context()
    t1 = time.time() * 1000
    try:
        yield
    except Exception as ex:
        logger.info('lock lost.')

        if str(ex).find('Lock wait timeout exceeded') != -1:
            stack = traceback.format_exc()
            logger.stacktrace(stack)

            raise error.DBLockTimeoutError('Actions failed.lt')

        exc_info = sys.exc_info()
        raise exc_info[0], exc_info[1], exc_info[2]

    else:
        logger.info('lock acquired.')

    finally:
        t2 = time.time() * 1000

        logger.info('exit lock context. time: %sms' % int(t2 - t1))  # noqa
        local.exit_lock_context()


@contextmanager
def open_transaction(database):
    logger.info('transaction start.')

    local.enter_trans_context()
    session = database.session
    try:
        yield
    except:
        logger.info('transaction rollback.')
        session.rollback()
        raise
    else:
        logger.info('transaction commit.')
        session.commit()
    finally:
        local.exit_trans_context()

        logger.info('transaction session remove.')
        session.remove()


def transaction(method):
    @functools.wraps(method)
    def wrap(*args, **kwargs):
        from densefog import db

        # if already in transaction context. just exe method.
        if local.in_trans_context():
            return method(*args, **kwargs)

        # else open new transaction context.
        with open_transaction(db.DB):
            return method(*args, **kwargs)

    return wrap
