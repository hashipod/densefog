from densefog import config
from densefog.common import db

DB = None


def setup():
    global DB

    DB = db.Database(get_connection())
    DB.echo_on(config.CONF.debug)


def get_connection():
    db_host = config.CONF.db_host
    db_port = config.CONF.db_port
    db_user = config.CONF.db_user
    db_passwd = config.CONF.db_password
    db_database = config.CONF.db_database
    return db.generate_engine_configuration(
        db_database,
        host=db_host,
        port=db_port,
        user=db_user,
        passwd=db_passwd)
