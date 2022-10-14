import flask
from densefog import bootstrap
from densefog import logger

from densefog.error_code import *

from densefog.common.service import Service


def index():
    response_data = """\
It\'s DenseFog API service.
"""
    response = flask.make_response(response_data, 200)
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    return response


def make_call(routes):
    from densefog import web
    from densefog.web import grand

    @grand.handle
    @web.log_user_operation
    @web.guard_resource_failure
    @web.guard_params_failure
    @web.guard_provider_failure
    @web.load_action_params
    def call():
        action = flask.request.action
        if action in routes:
            return routes[action]()
        else:
            raise grand.HandleError('Unknow action %s.' % action, ErrCodeRequestParamUnkownAction)

    return call


def route_blueprint(routes):
    assert bool(routes), 'routes is empty!'

    handler = make_call(routes)

    blueprint = flask.Blueprint('iaas', __name__)

    blueprint.add_url_rule('/', 'index', index, methods=['GET'])
    blueprint.add_url_rule('/', 'handler', handler, methods=['POST'])

    return blueprint


class API(object):
    def __init__(self, debug=False):
        self.service = Service(debug=debug)

    def route(self, routes):
        self.service.register(route_blueprint(routes), prefix='')
        return self

    def start(self, port):
        # save app port in config
        from densefog import config
        config.CONF.apply(app_port=port)

        self.service.start(port=port)


def create_api(name, debug=False):
    from densefog.server import ensure_config_setup
    ensure_config_setup()

    bootstrap.init()
    logger.init(dirname=name)

    return API(debug)
