import sys
from densefog import config
from densefog.server.api import create_api
from densefog.server.worker import create_worker

__all__ = [
    'create_api',
    'create_worker',
    'ensure_app_root'
]


def ensure_config_setup():
    assert bool(config.CONF), 'config should setup first!'

    app_root = getattr(config.CONF, 'app_root')
    assert bool(app_root), 'app root is not set!'

    log_path = getattr(config.CONF, 'log_path')
    assert bool(log_path), 'log path is not set!'

    if app_root not in sys.path:
        sys.path.append(app_root)
