# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""An in-process browser that acts as a WSGI server."""

from __future__ import absolute_import
import cookielib
import dummy_threading
from cStringIO import StringIO
from logging import getLogger
import os.path
from urlparse import urljoin, urlparse, urlunparse
from time import time
from wsgiref.util import request_uri

from blinker import signal
from werkzeug import (
    BaseResponse,
    FileStorage,
    MultiDict,
    create_environ,
    parse_cookie,
    run_wsgi_app,
    url_encode,
    )
from werkzeug.test import encode_multipart

from alfajor.browsers._lxml import (
    ButtonElement,
    DOMElement,
    DOMMixin,
    FormElement,
    InputElement,
    SelectElement,
    TextareaElement,
    html_parser_for,
    )
from alfajor.browsers._waitexpr import WaitExpression
from alfajor.utilities import lazy_property, to_pairs
from alfajor._compat import property


__all__ = ['WSGI']
logger = getLogger('tests.browser')
after_browser_activity = signal('after_browser_activity')
before_browser_activity = signal('before_browser_activity')


class WSGI(DOMMixin):

    capabilities = [
        'in-process',
        'cookies',
        'headers',
        'status',
        'upload',
        ]

    wait_expression = WaitExpression

    _wsgi_server = {
        'multithread': False,
        'multiprocess': False,
        'run_once': False,
        }

    user_agent = {
        'browser': 'wsgi',
        'platform': 'python',
        'version': '1.0',
        }

    def __init__(self, wsgi_app, base_url=None):
        # accept additional request headers?  (e.g. user agent)
        self._wsgi_app = wsgi_app
        self._base_url = base_url
        self._referrer = None
        self._request_environ = None
        self._cookie_jar = CookieJar()
        self._charset = 'utf-8'
        self.status_code = 0
        self.status = ''
        self.response = None
        self.headers = ()

    def open(self, url, wait_for=None, timeout=0):
        """Open web page at *url*."""
        self._open(url, refer=False)

    def reset(self):
        self._cookie_jar = CookieJar()

    @property
    def location(self):
        if not self._request_environ:
            return None
        return request_uri(self._request_environ)

    def wait_for(self, condition, timeout=None):
        pass

    def sync_document(self):
        """The document is always synced."""

    _sync_document = DOMMixin.sync_document

    @property
    def cookies(self):
        if not self._referrer:
            return {}
        environ = self._create_environ(self._referrer, 'GET', None, True)
        return parse_cookie(environ, self._charset)

    def set_cookie(self, name, value, domain=None, path=None):
        # TODO
        # create Cookie
        # self._cookie_jar.set_cookie(cookie)
        pass

    def delete_cookie(self, name, domain=None, path=None):
        # TODO
        try:
            self._cookie_jar.clear(domain, path, name)
        except KeyError:
            pass

    # Internal methods
    @lazy_property
    def _lxml_parser(self):
        return html_parser_for(self, wsgi_elements)

    def _open(self, url, method='GET', data=None, refer=True, content_type=None):
        before_browser_activity.send(self)
        open_started = time()
        environ = self._create_environ(url, method, data, refer, content_type)
        # keep a copy, the app may mutate the environ
        request_environ = dict(environ)

        logger.info('%s(%s) == %s', method, url, request_uri(environ))
        request_started = time()
        rv = run_wsgi_app(self._wsgi_app, environ)
        response = BaseResponse(*rv)
        # TODO:
        # response.make_sequence()  # werkzeug 0.6+
        # For now, must:
        response.response = list(response.response)
        if hasattr(rv[0], 'close'):
            rv[0].close()
        # end TODO

        # request is complete after the app_iter (rv[0]) has been fully read +
        # closed down.
        request_ended = time()

        self._request_environ = request_environ
        self._cookie_jar.extract_from_werkzeug(response, environ)
        self.status_code = response.status_code
        # Automatically follow redirects
        if 301 <= self.status_code <= 302:
            logger.debug("Redirect to %s", response.headers['Location'])
            after_browser_activity.send(self)
            self._open(response.headers['Location'])
            return
        # redirects report the original referrer
        self._referrer = request_uri(environ)
        self.status = response.status
        self.headers = response.headers
        # TODO: unicodify
        self.response = response.data
        self._sync_document()

        # TODO: what does a http-equiv redirect report for referrer?
        if 'meta[http-equiv=refresh]' in self.document:
            refresh = self.document['meta[http-equiv=refresh]'][0]
            if 'content' in refresh.attrib:
                parts = refresh.get('content').split(';url=', 1)
                if len(parts) == 2:
                    logger.debug("HTTP-EQUIV Redirect to %s", parts[1])
                    after_browser_activity.send(self)
                    self._open(parts[1])
                    return

        open_ended = time()
        request_time = request_ended - request_started
        logger.info("Fetched %s in %0.3fsec + %0.3fsec browser overhead",
                    url, request_time,
                    open_ended - open_started - request_time)
        after_browser_activity.send(self)

    def _create_environ(self, url, method, data, refer, content_type=None):
        """Return an environ to request *url*, including cookies."""
        environ_args = dict(self._wsgi_server, method=method)
        base_url = self._referrer if refer else self._base_url
        environ_args.update(self._canonicalize_url(url, base_url))
        environ_args.update(self._prep_input(method, data, content_type))
        environ = create_environ(**environ_args)
        if refer and self._referrer:
            environ['HTTP_REFERER'] = self._referrer
        environ.setdefault('REMOTE_ADDR', '127.0.0.1')
        self._cookie_jar.export_to_environ(environ)
        return environ

    def _canonicalize_url(self, url, base_url):
        """Return fully qualified URL components formatted for environ."""
        if '?' in url:
            url, query_string = url.split('?', 1)
        else:
            query_string = None

        canonical = {'query_string': query_string}

        # canonicalize against last request (add host/port, resolve
        # relative paths)
        if base_url:
            url = urljoin(base_url, url)

        parsed = urlparse(url)
        if not parsed.scheme:
            raise RuntimeError(
                "No base url available for resolving relative url %r" % url)

        canonical['path'] = urlunparse((
            '', '', parsed.path, parsed.params, '', ''))
        canonical['base_url'] = urlunparse((
            parsed.scheme, parsed.netloc, '', '', '', ''))
        return canonical

    def _prep_input(self, method, data, content_type):
        """Return encoded and packed POST data."""
        if data is None or method != 'POST':
            prepped = {
                'input_stream': None,
                'content_length': None,
                'content_type': None,
                }
            if method == 'GET' and data:
                qs = MultiDict()
                for key, value in to_pairs(data):
                    qs.setlistdefault(key).append(value)
                prepped['query_string'] = url_encode(qs)
            return prepped
        else:
            if content_type == 'multipart/form-data':
                data = [(k, _wrap_file(*v)) if isinstance(v, tuple) else (k,v)
                        for k,v in data]
                boundary, payload = encode_multipart(MultiDict(to_pairs(data)))
                content_type = 'multipart/form-data; boundary=' + boundary
            else:
                payload = url_encode(MultiDict(to_pairs(data)))
                content_type = 'application/x-www-form-urlencoded'
            return {
                'input_stream': StringIO(payload),
                'content_length': len(payload),
                'content_type': content_type
                }


def _wrap_file(filename, content_type):
    """Open the file *filename* and wrap in a FileStorage object."""
    assert os.path.isfile(filename), "File does not exist."
    return FileStorage(
        stream=open(filename, 'rb'),
        filename=os.path.basename(filename),
        content_type=content_type
    )


class FormElement(FormElement):
    """A <form/> that can be submitted."""

    def submit(self, wait_for=None, timeout=0, _extra_values=()):
        """Submit the form's values.

        Equivalent to hitting 'return' in a browser form: the data is
        submitted without the submit button's key/value pair.

        """
        if _extra_values and hasattr(_extra_values, 'items'):
            _extra_values = _extra_values.items()

        values = self.form_values()
        values.extend(_extra_values)
        method = self.method or 'GET'
        if self.action:
            action = self.action
        elif self.browser._referrer:
            action = urlparse(self.browser._referrer).path
        else:
            action = '/'
        self.browser._open(action, method=method, data=values,
                          content_type=self.get('enctype'))


class InputElement(InputElement):
    """An <input/> tag."""

    # Toss aside checkbox code present in the base lxml @value
    @property
    def value(self):
        return self.get('value')

    @value.setter
    def value(self, value):
        self.set('value', value)

    @value.deleter
    def value(self):
        if 'value' in self.attrib:
            del self.attrib['value']

    def click(self, wait_for=None, timeout=None):
        if self.checkable:
            self.checked = not self.checked
            return
        if self.type != 'submit':
            super(InputElement, self).click(wait_for, timeout)
            return
        for element in self.iterancestors():
            if element.tag == 'form':
                break
        else:
            # Not in a form: clicking does nothing.
            # TODO: probably not true
            return
        extra = ()
        if 'name' in self.attrib:
            extra = [[self.attrib['name'], self.attrib.get('value', 'Submit')]]
        element.submit(wait_for=wait_for, timeout=timeout, _extra_values=extra)


class ButtonElement(object):
    """Buttons that can be .click()ed."""

    def click(self, wait_for=None, timeout=0):
        # TODO: process type=submit|reset|button?
        for element in self.iterancestors():
            if element.tag == 'form':
                break
        else:
            # Not in a form: clicking does nothing.
            return
        pairs = []
        name = self.attrib.get('name', False)
        if name:
            pairs.append((name, self.attrib.get('value', '')))
        return element.submit(_extra_values=pairs)


class LinkElement(object):
    """Links that can be .click()ed."""

    def click(self, wait_for=None, timeout=0):
        try:
            link = self.attrib['href']
        except AttributeError:
            pass
        else:
            self.browser._open(link, 'GET')


wsgi_elements = {
    '*': DOMElement,
    'a': LinkElement,
    'button': ButtonElement,
    'form': FormElement,
    'input': InputElement,
    'select': SelectElement,
    'textarea': TextareaElement,
    }


class CookieJar(cookielib.CookieJar):
    """A lock-less CookieJar that can clone itself."""

    def __init__(self, policy=None):
        if policy is None:
            policy = cookielib.DefaultCookiePolicy()
        self._policy = policy
        self._cookies = {}
        self._cookies_lock = dummy_threading.RLock()

    def export_to_environ(self, environ):
        if len(self):
            u_request = _WSGI_urllib2_request(environ)
            self.add_cookie_header(u_request)

    def extract_from_werkzeug(self, response, request_environ):
        headers = response.headers
        if 'Set-Cookie' in headers or 'Set-Cookie2' in headers:
            u_response = _Werkzeug_urlib2_response(response)
            u_request = _WSGI_urllib2_request(request_environ)
            self.extract_cookies(u_response, u_request)


class _Duck(object):
    """Has arbitrary attributes assigned at construction time."""

    def __init__(self, **kw):
        for attr, value in kw.iteritems():
            setattr(self, attr, value)


class _Werkzeug_urlib2_response(object):
    __slots__ = 'response',

    def __init__(self, response):
        self.response = response

    def info(self):
        return _Duck(getallmatchingheaders=self.response.headers.getlist,
                     getheaders=self.response.headers.getlist)


class _WSGI_urllib2_request(object):

    def __init__(self, environ):
        self.environ = environ
        self.url = request_uri(self.environ)
        self.url_parts = urlparse(self.url)

    def get_full_url(self):
        return self.url

    def get_host(self):
        return self.url_parts.hostname

    def get_type(self):
        return self.url_parts.scheme

    def is_unverifiable(self):
        return False

    def get_origin_req_host(self):
        raise Exception('fixme need previous request')

    def has_header(self, header):
        key = header.replace('-', '_').upper()
        return key in self.environ or 'HTTP_%s' % key in self.environ

    def get_header(self, header):
        return self.environ.get('HTTP_%s' % header.replace('-', '_').upper())

    def header_items(self):
        items = []
        for key, value in self.environ.iteritems():
            if ((key.startswith('HTTP_') or key.startswith('CONTENT_')) and
                isinstance(value, basestring)):
                if key.startswith('HTTP_'):
                    key = key[5:]
                key = key.replace('_', '-').title()
                items.append((key, value))
        return items

    def add_unredirected_header(self, key, value):
        if key == 'Cookie':
            self.environ['HTTP_COOKIE'] = "%s: %s" % (key, value)
