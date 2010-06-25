# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""A low-level HTTP client suitable for testing APIs."""
import copy
from cStringIO import StringIO
import dummy_threading
from cookielib import DefaultCookiePolicy
from logging import DEBUG, getLogger
import mimetypes
from urllib import urlencode
from urlparse import urlparse, urlunparse
from wsgiref.util import request_uri

from werkzeug import BaseResponse, Headers, create_environ, run_wsgi_app
from werkzeug.test import _TestCookieJar, encode_multipart

from alfajor.utilities import eval_dotted_path
from alfajor._compat import json_loads as loads


logger = getLogger(__name__)

_json_content_types = set([
    'application/json',
    'application/x-javascript',
    'text/javascript',
    'text/x-javascript',
    'text/x-json',
    ])


class WSGIClientManager(object):
    """Lifecycle manager for global api clients."""

    def __init__(self, frontend_name, backend_config, runner_options):
        self.config = backend_config

    def create(self):
        from alfajor.apiclient import APIClient

        entry_point = self.config['server-entry-point']
        app = eval_dotted_path(entry_point)

        base_url = self.config.get('base_url')
        logger.debug("Created in-process WSGI api client rooted at %s.",
                     base_url)
        return APIClient(app, base_url=base_url)

    def destroy(self):
        logger.debug("Destroying in-process WSGI api client.")


class APIClient(object):

    def __init__(self, application, state=None, base_url=None):
        self.application = application
        self.state = state or _APIClientState(application)
        self.base_url = base_url

    def open(self, path='/', base_url=None, query_string=None, method='GET',
             data=None, input_stream=None, content_type=None,
             content_length=0, errors_stream=None, multithread=False,
             multiprocess=False, run_once=False, environ_overrides=None,
             buffered=True):

        parsed = urlparse(path)
        if parsed.scheme:
            if base_url is None:
                base_url = parsed.scheme + '://' + parsed.netloc
            if query_string is None:
                query_string = parsed.query
            path = parsed.path

        if (input_stream is None and
            data is not None and
            method in ('PUT', 'POST')):
            input_stream, content_length, content_type = \
                self._prep_input(input_stream, data, content_type)

        if base_url is None:
            base_url = self.base_url or self.state.base_url

        environ = create_environ(path, base_url, query_string, method,
                                 input_stream, content_type, content_length,
                                 errors_stream, multithread,
                                 multiprocess, run_once)

        current_state = self.state
        current_state.prepare_environ(environ)
        if environ_overrides:
            environ.update(environ_overrides)

        logger.info("%s %s" % (method, request_uri(environ)))
        rv = run_wsgi_app(self.application, environ, buffered=buffered)

        response = _APIClientResponse(*rv)
        response.state = new_state = current_state.copy()
        new_state.process_response(response, environ)
        return response

    def get(self, *args, **kw):
        """:meth:`open` as a GET request."""
        kw['method'] = 'GET'
        return self.open(*args, **kw)

    def post(self, *args, **kw):
        """:meth:`open` as a POST request."""
        kw['method'] = 'POST'
        return self.open(*args, **kw)

    def head(self, *args, **kw):
        """:meth:`open` as a HEAD request."""
        kw['method'] = 'HEAD'
        return self.open(*args, **kw)

    def put(self, *args, **kw):
        """:meth:`open` as a PUT request."""
        kw['method'] = 'PUT'
        return self.open(*args, **kw)

    def delete(self, *args, **kw):
        """:meth:`open` as a DELETE request."""
        kw['method'] = 'DELETE'
        return self.open(*args, **kw)

    def wrap_file(self, fd, filename=None, mimetype=None):
        """Wrap a file for use in POSTing or PUTing.

        :param fd: a file name or file-like object
        :param filename: file name to send in the HTTP request
        :param mimetype: mime type to send, guessed if not supplied.
        """
        return File(fd, filename, mimetype)

    def _prep_input(self, input_stream, data, content_type):
        if isinstance(data, basestring):
            assert content_type is not None, 'content type required'
        else:
            need_multipart = False
            pairs = []
            debugging = logger.isEnabledFor(DEBUG)
            for key, value in _to_pairs(data):
                if isinstance(value, basestring):
                    if isinstance(value, unicode):
                        value = str(value)
                    if debugging:
                        logger.debug("%r=%r" % (key, value))
                    pairs.append((key, value))
                    continue
                need_multipart = True
                if isinstance(value, tuple):
                    pairs.append((key, File(*value)))
                elif isinstance(value, dict):
                    pairs.append((key, File(**value)))
                elif not isinstance(value, File):
                    pairs.append((key, File(value)))
                else:
                    pairs.append((key, value))
            if need_multipart:
                boundary, data = encode_multipart(pairs)
                if content_type is None:
                    content_type = 'multipart/form-data; boundary=' + \
                        boundary
            else:
                data = urlencode(pairs)
                logger.debug('data: ' + data)
                if content_type is None:
                    content_type = 'application/x-www-form-urlencoded'
        content_length = len(data)
        input_stream = StringIO(data)
        return input_stream, content_length, content_type


class _APIClientResponse(object):
    state = None

    @property
    def client(self):
        """A new client born from this response.

        The client will have access to any cookies that were sent as part
        of this response & send this response's URL as a referrer.

        Each access to this property returns an independent client with its
        own copy of the cookie jar.

        """
        state = self.state
        return APIClient(application=state.application, state=state)

    status_code = BaseResponse.status_code

    @property
    def request_uri(self):
        """The source URI for this response."""
        return request_uri(self.state.source_environ)

    @property
    def is_json(self):
        """True if the response is JSON and the HTTP status was 200."""
        return (self.status_code == 200 and
                self.headers.get('Content-Type', '') in _json_content_types)

    @property
    def json(self):
        """The response parsed as JSON.

        No attempt is made to ensure the response is valid or even looks
        like JSON before parsing.
        """
        return loads(self.response)

    def __init__(self, app_iter, status, headers):
        self.headers = Headers(headers)
        if isinstance(status, (int, long)):
            self.status_code = status  # sets .status as well
        else:
            self.status = status

        if isinstance(app_iter, basestring):
            self.response = app_iter
        else:
            self.response = ''.join(app_iter)
        if 'Content-Length' not in self.headers:
            self.headers['Content-Length'] = len(self.response)


class _APIClientState(object):
    default_base_url = 'http://localhost'

    def __init__(self, application):
        self.application = application
        self.cookie_jar = _CookieJar()
        self.auth = None
        self.referrer = None

    @property
    def base_url(self):
        if not self.referrer:
            return self.default_base_url
        url = urlparse(self.referrer)
        return urlunparse(url[:2] + ('', '', '', ''))

    def copy(self):
        fork = copy.copy(self)
        fork.cookie_jar = self.cookie_jar.copy()
        return fork

    def prepare_environ(self, environ):
        if self.referrer:
            environ['HTTP_REFERER'] = self.referrer
        if len(self.cookie_jar):
            self.cookie_jar.inject_wsgi(environ)
        environ.setdefault('REMOTE_ADDR', '127.0.0.1')

    def process_response(self, response, request_environ):
        headers = response.headers
        if 'Set-Cookie' in headers or 'Set-Cookie2' in headers:
            self.cookie_jar.extract_wsgi(request_environ, headers)
        self.referrer = request_uri(request_environ)
        self.source_environ = request_environ


# lifted from werkzeug 0.4
class File(object):
    """Wraps a file descriptor or any other stream so that `encode_multipart`
    can get the mimetype and filename from it.
    """

    def __init__(self, fd, filename=None, mimetype=None):
        if isinstance(fd, basestring):
            if filename is None:
                filename = fd
            fd = file(fd, 'rb')
            try:
                self.stream = StringIO(fd.read())
            finally:
                fd.close()
        else:
            self.stream = fd
            if filename is None:
                if not hasattr(fd, 'name'):
                    raise ValueError('no filename for provided')
                filename = fd.name
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0]
        self.filename = filename
        self.mimetype = mimetype or 'application/octet-stream'

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.filename)


class _CookieJar(_TestCookieJar):
    """A lock-less, wsgi-friendly CookieJar that can clone itself."""

    def __init__(self, policy=None):
        if policy is None:
            policy = DefaultCookiePolicy()
        self._policy = policy
        self._cookies = {}
        self._cookies_lock = dummy_threading.RLock()

    def copy(self):
        fork = copy.copy(self)
        fork._cookies = copy.deepcopy(self._cookies)
        return fork


# taken from flatland
def _to_pairs(dictlike):
    """Yield (key, value) pairs from any dict-like object.

    Implements an optimized version of the dict.update() definition of
    "dictlike".

    """
    if hasattr(dictlike, 'items'):
        return dictlike.items()
    elif hasattr(dictlike, 'keys'):
        return [(key, dictlike[key]) for key in dictlike.keys()]
    else:
        return [(key, value) for key, value in dictlike]
