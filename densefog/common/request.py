
import urllib2


def post(url, payload, headers={}, logger=None, timeout=30, debug=False):
    """ Send post request to url with payload.
    default timeout is 30 seconds.

    url:        string
    payload:    string
    headers:    dict
    logger:     logger object which has `debug` method.
    timeout:    timeout for http request.
    """
    if logger and debug:
        logger.debug('post url: %s' % url)
        logger.debug('post payload: %s' % payload)

    req = urllib2.Request(url, payload)

    for k, v in headers.items():
        req.add_header(k, v)

    rsp = urllib2.urlopen(req, timeout=timeout)
    data = rsp.read()

    if logger:
        logger.debug('post response: %s' % data)

    return data
