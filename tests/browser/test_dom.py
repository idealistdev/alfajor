# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

from . import browser


def test_indexing():
    browser.open('/dom')
    doc = browser.document

    assert doc['#A'].tag == 'dl'
    assert doc['dl#A'].tag == 'dl'
    assert doc['body #A'].tag == 'dl'
    assert isinstance(doc['#A ul'], list)
    assert isinstance(doc['body #A ul'], list)
    assert doc['#C'][0].text == '1'
    assert len(doc['#C']['li']) == 2


def test_containment():
    browser.open('/dom')
    doc = browser.document

    assert 'dl' in doc
    assert '#C' in doc
    assert not '#C div' in doc
    assert 'li' in doc
    assert not 'div' in doc
    assert doc['body'][0] in doc
    assert not doc['#B'] in doc
    assert 0 in doc
    assert not 2 in doc


def test_xpath():
    browser.open('/dom')
    doc = browser.document

    assert doc['#A'].fq_xpath == '/html/body/dl'
    assert doc.xpath('/html/body/dl')[0] is doc['#A']


def test_innerhtml():
    browser.open('/dom')
    ps = browser.document['p']

    assert ps[0].innerHTML == 'msg 1'
    assert ps[1].innerHTML == 'msg<br>2'
    assert ps[2].innerHTML == 'msg<br>&amp;<br>3'
    assert ps[3].innerHTML == '<b>msg 4</b>'


def test_text_content():
    browser.open('/dom')
    ps = browser.document['p']

    assert ps[0].text_content == 'msg 1'
    assert ps[1].text_content == 'msg2'
    assert ps[2].text_content == 'msg&3'
    assert ps[2].text_content() == 'msg&3'
    assert ps[2].text == 'msg'
    assert ps[3].text_content == 'msg 4'


def test_visibility():
    browser.open('/dom')
    p = browser.document['p.hidden'][0]
    if 'visibility' in browser.capabilities:
        assert not p.is_visible
    else:
        assert p.is_visible
