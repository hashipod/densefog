import sys
import traceback
import datetime

import signal
import abc

from densefog import bootstrap
from densefog import logger


class JobNotifier(object):
    __metaclass__ = abc.ABCMeta

    topic = None

    def care(self, topic):
        return self.topic == topic

    @abc.abstractmethod
    def call(self, *args, **kwargs):
        pass


class Worker(object):
    def __init__(self,
                 pick_size=10,
                 exec_size=10,
                 exec_timeout=600,
                 gevent=True):
        """
        exec_size: gevent pool size, max running greenlets, default 10
        pick_size: how many jobs fetched from db at a time, default 10
        exec_timeout: how many seconds a execute try timeout, default 600s
        """
        event = None
        pool = None

        if gevent:
            import gevent as gvt
            from gevent.event import Event
            from gevent.pool import Pool

            event = Event()
            gvt.signal(signal.SIGQUIT, event.set)
            gvt.signal(signal.SIGTERM, event.set)
            gvt.signal(signal.SIGINT, event.set)
            pool = Pool(exec_size)

        else:
            raise ('Gevent is the only supported thread model '
                   'in worker by now! please set gevent=True')

        self.event = event
        self.pool = pool

        self.exec_timeout = exec_timeout
        self.pick_size = pick_size
        self.gevent = gevent

        self._init_logger()
        self._init_action_module()

        self.notifiers = []

    def _init_action_module(self):
        # hardcoded module path.
        action_module = 'model.job.action'
        __import__(action_module)
        self.action_module = sys.modules[action_module]

    def _init_logger(self):
        self.logger = logger.getChild(__file__)

    def start(self):
        from densefog.model.job import job as job_model
        from densefog.model.job import run_job

        self._clean()

        while True:
            try:
                jobs = job_model.limitation(status=job_model.JOB_STATUS_PENDING,  # noqa
                                            limit=self.pick_size,
                                            run_at=datetime.datetime.utcnow())
                if jobs['total'] == 0:
                    self.logger.info('fetched 0 jobs')
                else:
                    self.logger.info('fetched %s jobs. execute them sequencely' %  # noqa
                                len(jobs['items']))

                    for job in jobs['items']:
                        self.pool.spawn(run_job, job['id'], worker=self)

            except:
                stack = traceback.format_exc()
                self.logger.stacktrace(stack)

            if self.event.wait(timeout=2):
                self.pool.kill(block=True)
                self.pool.join(timeout=10)
                break

    def _clean(self):
        """
        if there is no running job, but in db, there are jobs status running,
        then we should clean jobs.

        update database, find running jobs and set their status to pending.

        reason: we may stop the worker when a job is being executed.
        then the database status will end up in 'running' state,
        but the job has been killed.
        """
        from densefog.model.job import job as job_model
        from densefog.model.job import clean_job

        try:
            jobs = job_model.limitation(status=job_model.JOB_STATUS_RUNNING,
                                        limit=0,
                                        run_at=datetime.datetime.utcnow())
            self.logger.info(('there are %d running jobs to clean') % jobs['total'])  # noqa
            for job in jobs['items']:
                self.pool.spawn(clean_job, job['id'])
        except:
            stack = traceback.format_exc()
            self.logger.stacktrace(stack)

        self.pool.join()

    def add_notifiers(self, notis):
        for noti in notis:
            self.add_notifier(noti)
        return self

    def add_notifier(self, noti):
        self.notifiers.append(noti)
        return self

    def notify(self, topic, job, *args, **kwargs):
        """Notify job running status to notifiers
        Those who are interested in the topic will get called
        """
        for noti in self.notifiers:
            if noti.care(topic):
                noti.call(job, *args, **kwargs)


def create_worker(**kwargs):
    from densefog.server import ensure_config_setup
    ensure_config_setup()

    bootstrap.init()
    logger.init(dirname='worker')

    return Worker(**kwargs)
