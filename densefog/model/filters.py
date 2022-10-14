from sqlalchemy.sql import and_, or_


def filter_ids(where, t, ids):
    if ids is None:
        pass
    elif len(ids) == 0:
        where = False
    else:
        where = and_(t.id.in_(ids), where)
    return where


def filter_names(where, t, names):
    if names is None:
        pass
    elif len(names) == 0:
        where = False
    else:
        where = and_(t.name.in_(names), where)
    return where


def filter_op_server_ids(where, t, op_server_ids):
    if op_server_ids is None:
        pass
    elif len(op_server_ids) == 0:
        where = False
    else:
        where = and_(t.op_server_id.in_(op_server_ids), where)
    return where


def filter_addresses(where, t, addresses):
    if addresses is None:
        pass
    elif len(addresses) == 0:
        where = False
    else:
        where = and_(t.address.in_(addresses), where)
    return where


def filter_op_floatingip_ids(where, t, op_floatingip_ids):
    if op_floatingip_ids is None:
        pass
    elif len(op_floatingip_ids) == 0:
        where = False
    else:
        where = and_(t.op_floatingip_id.in_(op_floatingip_ids), where)
    return where


def filter_project_ids(where, t, project_ids):
    if project_ids is None:
        pass
    elif len(project_ids) == 0:
        where = False
    else:
        where = and_(t.project_id.in_(project_ids), where)
    return where


def filter_network_ids(where, t, network_ids):
    if network_ids is None:
        pass
    elif len(network_ids) == 0:
        where = False
    else:
        where = and_(t.network_id.in_(network_ids), where)
    return where


def filter_image_ids(where, t, image_ids):
    if image_ids is None:
        pass
    elif len(image_ids) == 0:
        where = False
    else:
        where = and_(t.image_id.in_(image_ids), where)
    return where


def escape_for_like(str, esc):
    str = str.replace(esc, esc + esc)
    str = str.replace('_', esc + '_')
    str = str.replace('%', esc + '%')
    return str


def filter_search_word(where, t, search_word):
    if search_word is None:
        pass
    else:
        query = "%{0}%".format(escape_for_like(search_word, '='))
        where = and_(where,
                     or_(
                         t.name.like(query, escape='='),
                         t.id.like(query, escape='='),
                     ))
    return where


def filter_status(where, t, status):
    if status is None:
        pass
    else:
        if not isinstance(status, list):
            status = [status]
        where = and_(t.status.in_(status), where)
    return where


def filter_states(where, t, states):
    if states is None:
        pass
    else:
        if not isinstance(states, list):
            states = [states]
        where = and_(t.state.in_(states), where)
    return where


def filter_access_keys(where, t, keys):
    if keys is None:
        pass
    elif len(keys) == 0:
        where = False
    else:
        where = and_(t.key.in_(keys), where)
    return where


def filter_created_range(where, t, start, end):
    if start:
        where = and_(t.created >= start, where)
    if end:
        where = and_(t.created <= end, where)
    return where


def order_by(reverse):
    def _order_by(t):
        if reverse:
            return t.created.desc()
        else:
            return t.created.asc()
    return _order_by
