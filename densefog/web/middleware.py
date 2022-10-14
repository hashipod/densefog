import flask
import functools
from densefog import logger
from densefog import config
from densefog import error
from jsonschema import validate
from jsonschema import exceptions as json_error


def validate_request(schema):
    if flask.request.method == 'POST':
        silent = not config.CONF.debug
        params = flask.request.get_json(force=True, silent=silent)
    else:
        params = flask.request.args

    try:
        validate(params, schema)
    except json_error.ValidationError as e:
        raise error.ValidationError(e.message)

    return params


def _load_action_params():
    params = validate_request({
        'type': 'object',
        'properties': {
            'action': {'type': 'string'},
        },
        'required': ['action']
    })
    # although use the specific schema,
    # but returned params is the whole request params,
    # not just only the `action` param in the schema.
    flask.request.params = params
    flask.request.action = params['action']

    logger.info('load request action: %s' % flask.request.action)


def load_action_params(method):
    @functools.wraps(method)
    def wrap(*args, **kwargs):
        _load_action_params()
        return method(*args, **kwargs)
    return wrap
