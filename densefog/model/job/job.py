import sys
import time
import datetime
import json
import traceback
import gevent
from gevent import Timeout
from densefog import db
from densefog.common import utils
from densefog.model import base
from densefog.model import filters

from densefog import error

from sqlalchemy.sql import and_

from densefog import logger
logger = logger.getChild(__file__)

SYSTEM_JOB = utils.encode_uuid('00000000-0000-0000-0000-000000000000')

JOB_STATUS_PENDING = 'pending'
JOB_STATUS_RUNNING = 'running'
JOB_STATUS_FINISHED = 'finished'
JOB_STATUS_ERROR = 'error'

NOTIFY_JOB_STARTED = 'notify_job_started'
NOTIFY_JOB_FAILED = 'notify_job_failed'
NOTIFY_JOB_FINISHED = 'notify_job_finished'


class Job(base.StatusModel):

    @classmethod
    def db(cls):
        return db.DB.job

    def get_resources(self):
        try:
            return json.loads(self['params'])['resource_ids']
        except:
            return []

    def status_executable(self):
        return self['status'] in [
            JOB_STATUS_PENDING
        ]

    def status_resetable(self):
        return self['status'] in [
            JOB_STATUS_RUNNING
        ]

    def is_finished(self):
        return self['status'] == JOB_STATUS_FINISHED

    def is_error(self):
        return self['status'] == JOB_STATUS_ERROR

    def format(self):
        formated = {
            'jobId': self['id'],
            'projectId': self['project_id'],
            'action': self['action'],
            'status': self['status'],
            'resourceIds': self.get_resources(),
            'updated': self['updated'],
            'created': self['created'],
        }
        return formated


def get(job_id):
    job = Job.get_as_model(job_id)
    if job is None:
        raise error.JobNotFound(job_id)
    return job


def get_resources(job_id):
    job = get(job_id)
    return job.get_resources()


@utils.footprint(logger)
def fetch(job_id):
    """
    fetch a locked job. if the job is locked by other workers
    return None

    we wait at most timeout seconds to get the job from db.
    if not, return None
    """
    try:
        with base.lock_for_update():
            job = get(job_id)

    except error.DBLockTimeoutError:
        # normally we will not come here, because gevent Timeout is
        # much shorter than db lock timeout.
        stack = traceback.format_exc()
        logger.stacktrace(stack)

        # if get lock failed, means other worker is locking the job.
        logger.error('fetch job is locked by other workers, skip it.')
        return None
    else:
        return job


@utils.footprint(logger)
def prepare(job):
    update(job['id'], status=JOB_STATUS_RUNNING)


@utils.footprint(logger)
def reset(job):
    update(job['id'], status=JOB_STATUS_PENDING)


@utils.footprint(logger)
def execute(job, worker):
    timeout = worker.exec_timeout

    action = job['action']
    action_func = getattr(worker.action_module, utils.snake_case(action))

    params = json.loads(job['params'])
    params_safe = utils.hide_secret(params)

    logger.info('action: %s, params: %s' % (action, params_safe))

    if worker.gevent:
        time_sleep = gevent.sleep
    else:
        time_sleep = time.sleep

    t = Timeout(timeout)
    t.start()
    worker.notify(NOTIFY_JOB_STARTED, job)

    try:
        has_tried = job['trys'] + 1
        is_last_chance = (has_tried >= job['try_max'])
        result = action_func(params,
                             time_sleep=time_sleep,
                             is_last_chance=is_last_chance)
    except (Exception, Timeout) as ex:  # Timeout inherits from BaseException
        if isinstance(ex, Timeout):
            # this execution exceed 10 minutes, timeout.
            logger.error('exec_job timeout, didn\'t finish in %d seconds.' %
                         timeout)

        if isinstance(ex, error.IaasProviderActionError):
            stack = str(ex)
        elif isinstance(ex, error.BaseJobException):
            stack = str(ex)
        else:
            stack = traceback.format_exc()

        logger.stacktrace(stack)

        worker.notify(NOTIFY_JOB_FAILED, job,
                      exc_info=sys.exc_info(),
                      has_tried=has_tried,
                      is_last_chance=is_last_chance)

        logger.error('%s job, this try(%d) failed' % (action, has_tried))

        next_seconds = job['try_period'] * has_tried
        next_run_at = utils.seconds_later(next_seconds)

        if is_last_chance:
            # the job is failed indeed.
            update(job['id'],
                   status=JOB_STATUS_ERROR,
                   trys=has_tried,
                   params=json.dumps(params_safe),
                   error=str(ex))
            logger.error('reach max tries, confirmed failed.')
        else:
            # reschedule the job
            update(job['id'],
                   status=JOB_STATUS_PENDING,
                   trys=has_tried,
                   run_at=next_run_at)
            logger.info(('scheduled for next try at %s '
                         '(in %d secons)') %
                        (next_run_at, next_seconds))
    else:

        worker.notify(NOTIFY_JOB_FINISHED, job)

        # use may modify params (maybe params contains secret infomation?),
        # we save params back to db.
        update(job['id'],
               status=JOB_STATUS_FINISHED,
               trys=has_tried,
               error="",
               params=json.dumps(params_safe),
               result=json.dumps(result))

    finally:
        t.cancel()


def create(action,
           project_id=SYSTEM_JOB,
           params={},
           status=JOB_STATUS_PENDING,
           run_at=None,
           try_period=600,
           try_max=3):
    """
    action name is CamelCase.
    its snake_case is just identical to job/action.py function name.
    so if you create a new action,
    make sure it have related function in action.py

    run_at:
        the job will be run at some datetime.

    try_period:
        if the job is failed, it can be rescheduled after try_period later.
        default is one hour later.

    try_max:
        if the job failed, how many times it can be rescheduled.
        default is 3 times.

    """
    logger.info('.create() start. action: %s, project_id: %s, params: %s' %
                (action, project_id, params))

    if run_at is None:
        run_at = datetime.datetime.utcnow()

    job_id = Job.insert(**{
        'id': 'job-' + utils.generate_key(10),
        'project_id': project_id,
        'action': action,
        'status': status,
        'error': '',
        'result': '',
        'params': json.dumps(params),
        'updated': datetime.datetime.utcnow(),
        'created': datetime.datetime.utcnow(),
        'run_at': run_at,
        'try_period': try_period,
        'try_max': try_max,
        'trys': 0,

    })

    logger.info('.create() OK.')

    return job_id


def update(job_id, status=None,
           run_at=None, trys=None,
           error=None, params=None, result=None):
    logger.info('.udpate() start. job_id: %s' % job_id)

    get(job_id)
    updates = {}
    if status is not None:
        updates['status'] = status
    if run_at is not None:
        updates['run_at'] = run_at
    if trys is not None:
        updates['trys'] = trys
    if error is not None:
        updates['error'] = error
    if params is not None:
        updates['params'] = params
    if result is not None:
        updates['result'] = result

    updates['updated'] = datetime.datetime.utcnow()
    Job.update(job_id, **updates)
    logger.info('.udpate() OK.')


def limitation(project_ids=None, status=None, run_at=None, job_ids=None,
               offset=0, limit=10, reverse=True):
    logger.info('.limitation() start.')

    # if run_at is not specified, set a large value, so we can fetch as much
    # jobs as possible
    if run_at is None:
        run_at = datetime.datetime.utcnow() + datetime.timedelta(days=36500)

    def where(t):
        _where = True
        _where = filters.filter_ids(_where, t, job_ids)
        _where = filters.filter_project_ids(_where, t, project_ids)
        _where = filters.filter_status(_where, t, status)

        _where = and_(t.run_at <= run_at, _where)
        return _where

    page = Job.limitation_as_model(where,
                                   offset=offset,
                                   limit=limit,
                                   order_by=filters.order_by(reverse))
    logger.info('.limitation() OK.')
    return page
