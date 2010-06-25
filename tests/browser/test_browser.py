# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

import time

from nose.tools import raises

from . import browser


def test_simple():
    browser.open('/')

    if 'status' in browser.capabilities:
        assert browser.status_code == 200
        assert browser.status == '200 OK'
    if 'headers' in browser.capabilities:
        assert 'text/html' in browser.headers['Content-Type']
    assert not browser.cookies

    # This is generally not a safe assertion... the browser could (and does)
    # normalize the returned html in some fashion.
    assert browser.response == ('<html><head></head>'
                                '<body><p>hi there</p></body></html>')

    assert browser.document.cssselect('p')[0].text == 'hi there'


def test_reset():
    # TODO: flesh this out when cookie querying is working and has
    # test coverage.  until then, just verify that the method doesn't
    # explode.
    browser.open('/')
    browser.reset()


def test_user_agent():
    browser.open('/')
    ua = browser.user_agent
    assert ua['browser'] != 'unknown'


def test_traversal():
    browser.open('/seq/a')
    a_id = browser.document['#request_id'].text
    assert browser.cssselect('title')[0].text == 'seq/a'
    assert browser.location.endswith('/seq/a')
    assert not browser.cssselect('p.referrer')[0].text

    browser.cssselect('a')[0].click(wait_for='page')
    b_id = browser.document['#request_id'].text
    assert a_id != b_id
    assert browser.cssselect('title')[0].text == 'seq/b'
    assert browser.location.endswith('/seq/b')
    assert '/seq/a' in browser.cssselect('p.referrer')[0].text

    # bounce through a redirect
    browser.cssselect('a')[0].click(wait_for='page')
    d_id = browser.document['#request_id'].text
    assert d_id != b_id
    assert browser.cssselect('title')[0].text == 'seq/d'
    assert browser.location.endswith('/seq/d')
    assert '/seq/b' in browser.cssselect('p.referrer')[0].text


def _test_single_cookie(bounce):
    browser.open('/')
    assert not browser.cookies

    if bounce:
        landing_page = browser.location
        browser.open('/assign-cookie/1?bounce=%s' % landing_page)
    else:
        browser.open('/assign-cookie/1')

    assert browser.cookies == {'cookie1': 'value1'}

    browser.reset()
    assert not browser.cookies

    browser.open('/')
    assert not browser.cookies


def test_single_cookie():
    yield _test_single_cookie, False
    yield _test_single_cookie, True


def _test_multiple_cookies(bounce):
    browser.open('/')
    assert not browser.cookies

    if bounce:
        landing_page = browser.location
        browser.open('/assign-cookie/2?bounce=%s' % landing_page)
    else:
        browser.open('/assign-cookie/2')

    assert browser.cookies == {'cookie1': 'value1',
                               'cookie2': 'value 2'}

    browser.reset()
    assert not browser.cookies

    browser.open('/')
    assert not browser.cookies


def test_multiple_cookies():
    yield _test_multiple_cookies, False
    yield _test_multiple_cookies, True


def test_wait_for():
    # bare minimum no side-effects call browser.wait_for
    browser.wait_for('duration', 1)


def test_wait_for_duration():
    if 'selenium' in browser.capabilities:
        start = time.time()
        browser.open('/waitfor', wait_for='duration', timeout=1000)
        duration = time.time() - start
        assert duration >= 1


def test_wait_for_element():
    if 'selenium' in browser.capabilities:
        browser.open('/waitfor')
        browser.cssselect('a#appender')[0].click(
            wait_for='element:css=#expected_p', timeout=3000)
        assert browser.cssselect('#expected_p')


@raises(AssertionError)
def test_wait_for_element_not_found():
    if 'selenium' in browser.capabilities:
        browser.open('/waitfor')
        browser.wait_for('element:css=#unexisting', timeout=10)
    else:
        raise AssertionError('Ignore if not selenium')


def test_wait_for_element_not_present():
    if 'selenium' in browser.capabilities:
        browser.open('/waitfor')
        assert browser.cssselect('#removeme')
        browser.cssselect('#remover')[0].click(
            wait_for='!element:css=#removeme', timeout=3000)
        assert not browser.cssselect('#removeme')


def test_wait_for_ajax():
    if 'selenium' in browser.capabilities:
        browser.open('/waitfor')
        browser.cssselect('#ajaxappender')[0].click(
            wait_for='ajax', timeout=3000)
        assert len(browser.cssselect('.ajaxAdded')) == 3


def test_wait_for_js():
    if 'selenium' in browser.capabilities:
        browser.open('/waitfor')
        browser.cssselect('#counter')[0].click(
            wait_for='js:window.exampleCount==100;', timeout=3000)
