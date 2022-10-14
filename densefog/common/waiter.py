
import time
import gevent
import traceback
from densefog import config
from densefog.common import utils
from densefog import error

from densefog import logger
logger = logger.getChild(__file__)

WAITER_MAX_TIMEOUT = 60 * 60 * 24  # wait atmost 1 DAY.


def wait_object(fetcher, predicate, interrupt=None, patience=None,
                timeout=0):
    """
    Wait for object to become some predicate state.

    predicate: a function to test whether object is reach your state.
               accept an object as params
               example:
                   predicate = lambda obj: obj['status'] == 'available'

    interrupt: a function to test whether it should interrupt(stop waiting)
               accept an object as params
               default: None, no interrupt, wait forever till timeout.
               example:
                   interrupt = lambda obj: obj['status'] == 'error'

    patience: a function to calculate every wait time step.
               accept tried times as params
               default: None, no patience, sleep as short time as possible (1s)
               example:
                   patience = lambda tries: tries ** 0, wait 1s, 1s, 1s...
                   patience = lambda tries: tries ** 1, wait 1s, 2s, 3s...
                   patience = lambda tries: tries ** 2, wait 1s, 4s, 9s...
    """
    starttime = time.time()
    timeout = WAITER_MAX_TIMEOUT if timeout == 0 else timeout
    deadline = starttime + timeout
    tries = 0

    logger.info("wait action timeout: %d" % timeout)

    if config.CONF.gevent:
        time_sleep = gevent.sleep
    else:
        time_sleep = time.sleep

    try:
        obj = fetcher()
        while not predicate(obj):
            logger.debug("not ok yet...")
            if interrupt and interrupt(obj):
                raise error.WaitObjectInterrupt()
            elif time.time() > deadline:
                raise error.WaitObjectTimeout()
            else:
                tries += 1
                t = patience(tries) if patience else 1
                logger.debug("sleep for %d seconds" % t)
                time_sleep(t)

            obj = fetcher()

    except (error.WaitObjectInterrupt, error.WaitObjectTimeout) as ex:  # noqa
        logger.error('wait get exception: %s' % ex)
        logger.error('wait object: %s' % obj)
        raise

    except Exception as ex:
        stack = traceback.format_exc()

        if ex.__class__.__name__.find('NotFound') != -1:
            raise error.WaitObjectNotFound(ex, stack)
        else:
            raise error.BaseWaiterError(ex, stack)

    return obj


@utils.footprint(logger)
def wait_deleted(fetcher, patience=None, timeout=None):
    """
    Wait for object to be deleted

    patience: a function to calculate every wait time step.
               accept tried times as params
               default: None, no patience, sleep as short time as possible (1s)
               example:
                   patience = lambda tries: tries ** 0, wait 1s, 1s, 1s...
                   patience = lambda tries: tries ** 1, wait 1s, 2s, 3s...
                   patience = lambda tries: tries ** 2, wait 1s, 4s, 9s...

    """
    starttime = time.time()
    timeout = WAITER_MAX_TIMEOUT if timeout == 0 else timeout
    deadline = starttime + timeout
    tries = 0

    logger.info("wait deleted action timeout: %d" % timeout)

    if config.CONF.gevent:
        time_sleep = gevent.sleep
    else:
        time_sleep = time.sleep

    try:
        fetcher()
        while True:
            logger.debug("not deleted yet...")

            if time.time() > deadline:
                raise error.WaitObjectTimeout()

            tries += 1
            t = patience(tries) if patience else 1
            logger.debug("sleep for %d seconds" % t)
            time_sleep(t)

            fetcher()
    except error.WaitObjectTimeout:
        raise

    except Exception as ex:
        if ex.__class__.__name__.find('NotFound') != -1:
            pass
        else:
            stack = traceback.format_exc()
            raise error.BaseWaiterError(ex, stack)
