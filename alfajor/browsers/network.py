# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""A browser backend that talks over a network socket to a web server."""

from __future__ import absolute_import
from cookielib import Cookie, CookieJar
from logging import getLogger
import urllib2
from urllib import urlencode
from urlparse import urljoin
from time import time

from blinker import signal
from werkzeug import Headers

from alfajor.browsers._lxml import DOMMixin, html_parser_for
from alfajor.browsers._waitexpr import WaitExpression
from alfajor.browsers.wsgi import wsgi_elements
from alfajor.utilities import lazy_property
from alfajor._compat import property


__all__ = ['Network']
logger = getLogger('tests.browser')
after_browser_activity = signal('after_browser_activity')
before_browser_activity = signal('before_browser_activity')


class Network(DOMMixin):

    capabilities = [
        'cookies',
        'headers',
        ]

    wait_expression = WaitExpression

    user_agent = {
        'browser': 'network',
        'platform': 'python',
        'version': '1.0',
        }

    def __init__(self, base_url=None):
        # accept additional request headers?  (e.g. user agent)
        self._base_url = base_url
        self.reset()

    def open(self, url, wait_for=None, timeout=0):
        """Open web page at *url*."""
        self._open(url)

    def reset(self):
        self._referrer = None
        self._request_environ = None
        self._cookie_jar = CookieJar()
        self._opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self._cookie_jar)
        )
        self.status_code = 0
        self.status = ''
        self.response = None
        self.location = None
        self.headers = ()

    def wait_for(self, condition, timeout=None):
        pass

    def sync_document(self):
        """The document is always synced."""

    _sync_document = DOMMixin.sync_document

    @property
    def cookies(self):
        if not (self._cookie_jar and self.location):
            return {}
        request = urllib2.Request(self.location)
        policy = self._cookie_jar._policy
        return dict(
            ((cookie.name,
              cookie.value[1:-1] if cookie.value.startswith('"') else cookie.value)
            for cookie in self._cookie_jar
            if policy.return_ok(cookie, request))
        )

    def set_cookie(self, name, value, domain=None, path=None,
                   session=True, expires=None, port=None):
#        Cookie(version, name, value, port, port_specified,
#                 domain, domain_specified, domain_initial_dot,
#                 path, path_specified, secure, expires,
#                 discard, comment, comment_url, rest,
#                 rfc2109=False):

        cookie = Cookie(0, name, value, port, bool(port),
                        domain or '', bool(domain),
                        (domain and domain.startswith('.')),
                        path or '', bool(path), False, expires,
                        session, None, None, {}, False)
        self._cookie_jar.set_cookie(cookie)

    def delete_cookie(self, name, domain=None, path=None):
        try:
            self._cookie_jar.clear(domain, path, name)
        except KeyError:
            pass

    # Internal methods
    @lazy_property
    def _lxml_parser(self):
        return html_parser_for(self, wsgi_elements)

    def _open(self, url, method='GET', data=None, refer=True,
              content_type=None):
        before_browser_activity.send(self)
        open_started = time()

        if data:
            data = urlencode(data)

        url = urljoin(self._base_url, url)
        if method == 'GET':
            if '?' in url:
                url, query_string = url.split('?', 1)
            else:
                query_string = None

            if data:
                query_string = data
            if query_string:
                url = url + '?' + query_string

            request = urllib2.Request(url)
        elif method == 'POST':
            request = urllib2.Request(url, data)
        else:
            raise Exception('Unsupported method: %s' % method)
        if self._referrer and refer:
            request.add_header('Referer', self._referrer)

        logger.info('%s(%s)', url, method)
        request_started = time()

        response = self._opener.open(request)

        request_ended = time()

        self.status_code = response.getcode()
        self.headers = Headers(
            (head.strip().split(': ',1) for head in response.info().headers)
        )
        self._referrer = request.get_full_url()
        self.location = response.geturl()
        self._response = response
        self.response = ''.join(list(response))
        self._sync_document()

        open_ended = time()
        request_time = request_ended - request_started

        logger.info("Fetched %s in %0.3fsec + %0.3fsec browser overhead",
                    url, request_time,
                    open_ended - open_started - request_time)
        after_browser_activity.send(self)


