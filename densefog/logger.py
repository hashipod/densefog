import os
import traceback

import logging

from densefog import config
from densefog.common import local

ACCESS = None
NORMAL = None

DIR = None


class ContextFormatter(logging.Formatter):

    def format(self, record):
        record.contextId = local.get_context_id()
        return logging.Formatter.format(self, record)


def init(dirname):
    if config.CONF.debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    setup_log_path(dirname)

    setup_access_log(level)
    setup_normal_log(level)
    setup_db_log(level)


def setup_log_path(dirname):
    global DIR

    log_path = config.CONF.log_path
    if not log_path:
        log_path = os.path.join(config.CONF.app_root, '..', 'logs')
        if not os.path.exists(log_path):
            os.makedirs(log_path)

    DIR = os.path.join(log_path, dirname)

    if not os.path.exists(DIR):
        os.makedirs(DIR)


def setup_access_log(level):
    global ACCESS

    log_file = os.path.join(DIR, 'access.log')

    fmt = '[{port}][{pid}]'.format(port=config.CONF.app_port, pid=os.getpid())  # noqa
    fmt += '[%(asctime)s][%(contextId)s] %(message)s'

    ACCESS = init_logger('access', fmt, level, log_file)


def setup_normal_log(level):
    global NORMAL

    log_file = os.path.join(DIR, 'normal.log')

    fmt = '[%(levelname)s][%(asctime)s][%(contextId)s][%(name)s] %(message)s'
    NORMAL = init_logger('root', fmt, level, log_file)


def init_logger(logger_name, fmt, level, logger_file=None):
    """
    if set logger_file, use rotated file handler,
    else just use stream handler to print log to stderr.

    logger object itself use DEBUG to allow every log.
    file handler use specific level to filter some log when write file.
    stream handler use DEBUG print every log.

    in production, always set logger_file.

    """
    try:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

        handler = get_handler(level, fmt, logger_file)

        logger.addHandler(handler)
        return logger
    except:
        print("Failed to init logger: %s" % logger_name)
        print(traceback.format_exc())


def setup_db_log(level):
    log_file = os.path.join(DIR, 'sql.log')

    fmt = '[%(asctime)s][%(contextId)s] %(message)s'
    handler = get_handler(level, fmt, log_file)

    logger = logging.getLogger('sqlalchemy')
    logger.propagate = False
    logger.setLevel(level)
    logger.addHandler(handler)


def get_handler(level, fmt, logger_file=None):
    if logger_file:
        handler = logging.FileHandler(logger_file)
        handler.setLevel(level)
    else:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)

    handler.setFormatter(ContextFormatter(fmt))

    return handler


# log levels:
#
# CRITICAL = 50
# FTAL = CRITICAL
# ERROR = 40
# WARNING = 30
# WARN = WARNING
# INFO = 20
# DEBUG = 10


def critical(msg, *args, **kwargs):
    NORMAL.critical(msg, *args, **kwargs)


fatal = critical


def stacktrace(traceback, *args, **kwargs):
    msg = "%s-%s" % (local.get_context_id(), traceback)

    NORMAL.critical(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    NORMAL.critical(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    NORMAL.warning(msg, *args, **kwargs)


warn = warning


def info(msg, *args, **kwargs):
    NORMAL.info(msg, *args, **kwargs)


def debug(msg, *args, **kwargs):
    NORMAL.debug(msg, *args, **kwargs)


def getChild(deep_file):
    p2 = os.path.realpath(deep_file)
    p3 = os.path.relpath(p2, config.CONF.app_root)

    child = NORMAL.getChild(p3)

    # add stacktrace
    child.stacktrace = stacktrace

    return child
