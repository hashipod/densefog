
import json
import datetime
from densefog import db
from densefog.common import model
from densefog.common import utils
from densefog.model import filters

from densefog import logger
logger = logger.getChild(__file__)


class Operation(model.Model):

    @classmethod
    def db(cls):
        return db.DB.operation

    def format(self):
        return {
            'operationId': self['id'],
            'projectId': self['project_id'],
            'accessKey': self['access_key'],
            'action': self['action'],
            'params': json.loads(self['params']),
            'retCode': self['ret_code'],
            'resourceType': self['resource_type'],
            'resourceIds': json.loads(self['resource_ids']),
            'retMessage': self['ret_message'],
            'updated': self['updated'],
            'created': self['created'],
        }


def create(project_id, access_key, action, params,
           resource_type, resource_ids, ret_code, ret_message):
    logger.info('.create() start. ')

    try:
        resource_ids = json.dumps(resource_ids)
    except:
        resource_ids = []

    if ret_message:
        ret_message = ret_message[0:100]

    opertn_id = Operation.insert(**{
        'id': 'opertn-' + utils.generate_key(10),
        'project_id': project_id,
        'access_key': access_key,
        'action': action,
        'params': json.dumps(params),
        'resource_type': resource_type,
        'resource_ids': resource_ids,
        'ret_code': ret_code,
        'ret_message': ret_message,
        'updated': datetime.datetime.utcnow(),
        'created': datetime.datetime.utcnow(),
    })
    logger.info('.create() OK. ')

    return opertn_id


def limitation(project_ids=None, created_start=None, created_end=None,
               offset=0, limit=10, reverse=True):
    def where(t):
        _where = True
        _where = filters.filter_project_ids(_where, t, project_ids)
        _where = filters.filter_created_range(_where, t, created_start, created_end)  # noqa
        return _where

    logger.info('.limitation() start. ')
    page = Operation.limitation_as_model(where,
                                         offset=offset,
                                         limit=limit,
                                         order_by=filters.order_by(reverse))
    logger.info('.limitation() OK. ')
    return page
