import json
import time
import pymysql
from mock import MagicMock


def _prepare_mysql():
    cursor = pymysql.connect(host='localhost',
                             port=3306,
                             user='root',
                             passwd='root').cursor()
    try:
        cursor.execute('drop database test')
        cursor.fetchone()
    except:
        pass
    cursor.execute('create database test')
    cursor.fetchone()


def create_db():
    from densefog.dba import actions
    from densefog import db

    _prepare_mysql()

    db.setup()
    db.DB.echo_on(False)

    actions.migrate()


def reset_db():
    from densefog import db

    try:
        cursor = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 passwd='root').cursor()

        sql = """
            SELECT Concat('TRUNCATE TABLE ',table_schema,'.',TABLE_NAME, ';')
            FROM INFORMATION_SCHEMA.TABLES where table_schema in ('test');
        """
        cursor.execute(sql)
        queries = cursor.fetchall()
        for query in queries:
            cursor.execute(query[0])
            cursor.fetchone()
    except:
        raise

    # remove old session.
    db.DB.session.remove()


def _mock_logger():
    """
    mock logger so that it do not write useless log file when running nosetest
    ignore every thing.
    """
    logger = logging.getLogger('test')
    formatter = logging.Formatter("%(asctime)s;%(levelname)s;%(message)s", "%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def mock_env():
    from densefog import bootstrap
    from densefog import db
    from densefog import logger

    _prepare_mysql()

    db.get_connection = MagicMock()
    db.get_connection.return_value = \
        'mysql+pymysql://root:root@localhost:3306/test'

    # logger.init_logger = MagicMock()
    # logger.init_logger.return_value = _mock_logger()

    bootstrap.init()
    logger.init(name='tests')

    create_db()


def wait_all_jobs():
    from densefog.model.job import job as job_model
    from densefog.model.job import action as job_action
    from densefog.common import utils

    jobs = job_model.limitation(status=job_model.JOB_STATUS_PENDING)
    for job in jobs['items']:
        job_id = job['id']
        params = json.loads(job['params'])
        func_name = utils.snake_case(job['action'])
        action_func = getattr(job_action, func_name)
        job_model.update(job_id, status=job_model.JOB_STATUS_RUNNING)
        result = action_func(params, time_sleep=time.sleep)
        job_model.update(job_id,
                         status=job_model.JOB_STATUS_FINISHED,
                         result=json.dumps(result))


mock_env()
