import os
import sys
import json

import time
import random

from densefog.server import create_api
from densefog import config

from densefog.error_code import *
from densefog import error

import pytest


# tool function to wrap exception lambda
def raise_(ex):
    raise ex


@pytest.fixture
def api():
    now = str(time.time()) + str(random.randint(1, 100))
    config.setup().apply(**{
        'app_root': os.path.dirname(os.path.abspath(__file__)),
        'log_path': '/tmp/densefog_test/' + str(now)
    })

    api = create_api('test', debug=True)
    # no need to start listening.
    # api.start(port=8080)
    return api


class Test:

    def test_base_dummy_get_api(self, api):
        api.route({
            'a': lambda: 'b',
        })
        client = api.service.app.test_client()
        result = client.get('/')
        assert 200 == result.status_code

    def test_guard_request_param_exceptions(self, api):
        api.route({
            'ActionName': lambda: {'text': 'hello world'},
        })
        client = api.service.app.test_client()

        # empty body
        result = client.post('/')
        assert 200 == result.status_code
        body = json.loads(result.data)
        assert body['retCode'] == ErrCodeRequestParamValidationError
        assert "Illegal request format" in body['message']

        # unkown action
        result = client.post('/', json={
            'action': 'SomeOhterAction'
        })
        assert 200 == result.status_code
        body = json.loads(result.data)
        assert body['retCode'] == ErrCodeRequestParamUnkownAction
        assert "Unknow action" in body['message']

        # correct param
        result = client.post('/', json={
            'action': 'ActionName'
        })
        assert 200 == result.status_code
        body = json.loads(result.data)
        assert body['retCode'] == ErrCodeOK
        assert body['data']['text'] == 'hello world'

    def test_guard_resource_related_exceptions(self, api):
        resource_id = 1
        api.route({
            'ActionResourceNotFound': lambda: raise_(error.ResourceNotFound(resource_id)),
            'ActionResourceNotBelongsToProject': lambda: raise_(error.ResourceNotBelongsToProject(resource_id)),
            'ActionResourceActionForbiden': lambda: raise_(error.ResourceActionForbiden(resource_id)),
            'ActionResourceActionUnsupported': lambda: raise_(error.ResourceActionUnsupported(resource_id)),
            'ActionResourceIsBusy': lambda: raise_(error.ResourceIsBusy(resource_id)),
        })
        client = api.service.app.test_client()

        result = client.post('/', json={
            'action': 'ActionResourceNotFound'
        })
        body = json.loads(result.data)
        assert body['retCode'] == ErrCodeResourceNotFound

        result = client.post('/', json={
            'action': 'ActionResourceNotBelongsToProject'
        })
        body = json.loads(result.data)
        assert body['retCode'] == ErrCodeResourceNotBelongsToProject

        result = client.post('/', json={
            'action': 'ActionResourceActionForbiden'
        })
        body = json.loads(result.data)
        assert body['retCode'] == ErrCodeResourceActionForbiden

        result = client.post('/', json={
            'action': 'ActionResourceActionUnsupported'
        })
        body = json.loads(result.data)
        assert body['retCode'] == ErrCodeResourceActionUnsupported

        result = client.post('/', json={
            'action': 'ActionResourceIsBusy'
        })
        body = json.loads(result.data)
        assert body['retCode'] == ErrCodeResourceActionForbiden

    def test_guard_provider_exceptions(self, api):
        resource_id = 1
        api.route({
            'SomeAction': lambda: raise_(error.IaasProviderActionError("ex", "stack", "some inner error message logged in logfile")),
        })
        client = api.service.app.test_client()

        result = client.post('/', json={
            'action': 'SomeAction'
        })
        body = json.loads(result.data)
        assert body['retCode'] == ErrCodeProviderError
        assert 'Action failed.op' == body['message']
