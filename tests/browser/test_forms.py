# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

from alfajor._compat import json_loads as loads

from nose.tools import eq_, raises
import os.path

from . import browser


def test_get():
    for index in 0, 1, 2:
        browser.open('/form/methods')
        assert browser.document['#get_data'].text == '[]'
        data = {
            'first_name': 'Tester',
            'email': 'tester@tester.com',
        }
        form = browser.document.forms[index]
        form.fill(data)
        form.submit(wait_for='page')
        get = loads(browser.document['#get_data'].text)
        post = loads(browser.document['#post_data'].text)
        assert get == [['email', 'tester@tester.com'],
                       ['first_name', 'Tester']]
        assert not post


def test_get_qs_append():
    # "blank" submit should round trip stuff in the query string
    browser.open('/form/methods?stuff=already&in=querystring')
    form = browser.document.forms[3]
    form.submit(wait_for='page')
    get = loads(browser.document['#get_data'].text)
    post = loads(browser.document['#post_data'].text)
    assert sorted(get) == [['email', ''], ['first_name', '']]
    assert post == []

    # amended submit should include existing stuff plus new submission
    browser.open('/form/methods?stuff=already&in=querystring')
    form = browser.document.forms[3]
    form.fill({'email': 'snorgle'})
    form.submit(wait_for='page')
    get = loads(browser.document['#get_data'].text)
    post = loads(browser.document['#post_data'].text)
    assert sorted(get) == [['email', 'snorgle'], ['first_name', '']]
    assert post == []


def test_post():
    browser.open('/form/methods')
    assert browser.document['#post_data'].text == '[]'
    data = {
        'first_name': 'Tester',
        'email': 'tester@tester.com',
    }
    form = browser.document.forms[4]
    form.fill(data)
    form.submit(wait_for='page')
    get = loads(browser.document['#get_data'].text)
    post = loads(browser.document['#post_data'].text)
    assert not get
    assert sorted(post) == [['email', 'tester@tester.com'],
                            ['first_name', 'Tester']]


def test_post_qs_append():
    browser.open('/form/methods?x=y')
    assert browser.document['#post_data'].text == '[]'
    data = {
        'first_name': 'Tester',
        'email': 'tester@tester.com',
    }
    form = browser.document.forms[5]
    form.fill(data)
    form.submit(wait_for='page')
    get = loads(browser.document['#get_data'].text)
    post = loads(browser.document['#post_data'].text)
    assert sorted(get) == [['x', 'y']]
    assert sorted(post) == [['email', 'tester@tester.com'],
                            ['first_name', 'Tester']]

    browser.open('/form/methods?x=y&email=a')
    assert browser.document['#post_data'].text == '[]'
    data = {
        'first_name': 'Tester',
        'email': 'tester@tester.com',
    }
    form = browser.document.forms[5]
    form.fill(data)
    form.submit(wait_for='page')
    get = loads(browser.document['#get_data'].text)
    post = loads(browser.document['#post_data'].text)
    assert sorted(get) == [['email', 'a'], ['x', 'y']]
    assert sorted(post) == [['email', 'tester@tester.com'],
                            ['first_name', 'Tester']]


def test_submit_buttonless():
    for idx in 0, 1:
        browser.open('/form/submit')
        browser.document.forms[idx].submit(wait_for='page')
        data = loads(browser.document['#data'].text)
        assert data == [['search', '']]


def test_nameless_submit_button():
    for idx in 2, 3:
        browser.open('/form/submit')
        button = browser.document.forms[idx]['input[type=submit]'][0]
        button.click(wait_for='page')
        data = loads(browser.document['#data'].text)
        assert data == [['search', '']]


def test_named_submit_button():
    for idx in 4, 5, 6:
        browser.open('/form/submit')
        assert browser.document['#method'].text == 'GET'
        button = browser.document.forms[idx]['input[type=submit]'][0]
        button.click(wait_for='page')
        assert browser.document['#method'].text == 'POST'
        data = loads(browser.document['#data'].text)
        assert sorted(data) == [['search', ''], ['submitA', 'SubmitA']]


def test_valueless_submit_button():
    browser.open('/form/submit')
    button = browser.document.forms[7]['input[type=submit]'][0]
    button.click(wait_for='page')
    data = loads(browser.document['#data'].text)
    assert len(data) == 2
    data = dict(data)
    assert data['search'] == ''
    # the value sent is browser implementation specific.  could be
    # Submit or Submit Query or ...
    assert data['submitA'] and data['submitA'] != ''


def test_multielement_submittal():
    browser.open('/form/submit')
    assert browser.document['#method'].text == 'GET'

    browser.document.forms[8].submit(wait_for='page')
    assert browser.document['#method'].text == 'POST'
    data = loads(browser.document['#data'].text)
    assert sorted(data) == [['x', ''], ['y', '']]

    browser.open('/form/submit')
    assert browser.document['#method'].text == 'GET'
    button = browser.document.forms[8]['input[type=submit]'][0]
    button.click(wait_for='page')
    assert browser.document['#method'].text == 'POST'
    data = loads(browser.document['#data'].text)
    assert sorted(data) == [['submitA', 'SubmitA'], ['x', ''], ['y', '']]


def test_textarea():
    browser.open('/form/textareas')
    browser.document.forms[0].submit(wait_for='page')
    data = loads(browser.document['#data'].text_content)
    assert data == [['ta', '']]

    browser.document.forms[0]['textarea'][0].value = 'foo\r\nbar'
    browser.document.forms[0].submit(wait_for='page')
    data = loads(browser.document['#data'].text_content)
    assert data == [['ta', 'foo\r\nbar']]

    textarea = browser.document.forms[0]['textarea'][0]
    textarea.enter('baz')
    textarea.enter('\r\nquuX\r\n')
    textarea.enter('\x08\x08x')
    browser.document.forms[0].submit(wait_for='page')
    data = loads(browser.document['#data'].text_content)
    assert data == [['ta', 'baz\r\nquux']]

def test_multipart_simple():
    if 'upload' not in browser.capabilities:
        return

    browser.open('/form/multipart')
    data = loads(browser.document['#data'].text_content)
    assert data == []

    browser.document.forms[0]['input[name=search]'][0].value = 'foobar'
    browser.document.forms[0].submit(wait_for='page')
    data = loads(browser.document['#data'].text_content)
    assert data == [['search', 'foobar']]


def test_multipart_file():
    if 'upload' not in browser.capabilities:
        return

    browser.open('/form/multipart')
    files = loads(browser.document['#files'].text_content)
    assert files == []

    filename = os.path.join(os.path.dirname(__file__),
                            'images', 'bread.jpg')
    browser.document.forms[1]['input[name=file]'][0].value = filename
    browser.document.forms[1].submit(wait_for='page')
    files = loads(browser.document['#files'].text_content)

    #[[u'file', [u'bread.jpg', u'image/jpeg', 0,
    # u'/var/folders/1v/1vxraEFhFWSxUV1jAExVYE+++TI/-Tmp-/tmptsBwrz']]]

    assert files[0][0] == 'file'
    assert files[0][1][0:2] == [os.path.basename(filename), 'image/jpeg']
    resaved_name = files[0][1][3]
    original_stat = os.stat(filename)
    new_stat = os.stat(resaved_name)
    os.remove(resaved_name)
    assert original_stat.st_size == new_stat.st_size


def test_formless_submit_button():
    browser.open('/form/submit')
    assert browser.document['#method'].text == 'GET'
    request_id = browser.document['#request_id'].text

    browser.document['#floater'].click()
    assert browser.document['#request_id'].text == request_id


def test_select_default_initial_empty():
    browser.open('/form/select')
    browser.document.forms[0]['input[type=submit]'][0].click()
    data = loads(browser.document['#data'].text)
    assert data == [['sel', '']]


def _test_select(form_num, fieldname, value, expected_return):
    """Repeat tests with multiple lxml <select> value setting strategies."""

    def set_value():
        browser.document.forms[form_num]['select'][0].value = value

    def assign_to_field():
        browser.document.forms[form_num].fields[fieldname] = value

    def fill():
        browser.document.forms[form_num].fill({fieldname: value})

    for strategy in set_value, assign_to_field, fill:
        browser.open('/form/select')
        strategy()
        browser.document.forms[form_num]['input[type=submit]'][0].click()
        data = loads(browser.document['#data'].text)
        eq_(data, [[fieldname, expected_return]])


def test_select_empty():
    _test_select(0, 'sel', None, '')


def test_select_empty_value():
    _test_select(1, 'sel', '', '')


def test_select_value_only():
    _test_select(0, 'sel', 'val_only', 'val_only')


def test_select_text_only():
    _test_select(0, 'sel', 'text only', 'text only')


def test_select_combo():
    _test_select(0, 'sel', 'combo', 'combo')


def test_basic_checkbox_state():
    browser.open('/form/checkboxes')
    fields = browser.document['form'][0]['input[type=checkbox]']
    assert not fields[0].checked
    assert not fields[1].checked
    assert not fields[2].checked
    assert fields[3].checked

    assert fields[3].value == 'x4'

    fields[2].checked = True
    fields[3].checked = False
    assert fields[3].value == 'x4'

    assert fields[2].checked
    assert not fields[3].checked

    fields[3].checked = True

    assert fields[3].value == 'x4'


def test_checkbox_indirection():
    browser.open('/form/checkboxes')

    form = browser.document.forms[1]
    assert form.fields['y'] == ''
    assert form.fields['z'] == 'z1'

    form.fields['y'] = 'y1'
    form.fields['z'] = False

    assert form.fields['y'] == 'y1'
    assert form.inputs['y'][0].checked
    assert form.inputs['y'][0].value == 'y1'

    assert form.fields['z'] == ''
    assert not form.inputs['z'][0].checked
    assert form.inputs['z'][0].value == 'z1'

    form.fields['y'] = ''
    form.fields['z'] = True

    assert form.fields['y'] == ''
    assert not form.inputs['y'][0].checked
    assert form.inputs['y'][0].value == 'y1'

    assert form.fields['z'] == 'z1'
    assert form.inputs['z'][0].checked
    assert form.inputs['z'][0].value == 'z1'

    form.fields = {'y': 'y1', 'z': ''}

    assert form.fields['y'] == 'y1'
    assert form.inputs['y'][0].checked
    assert form.inputs['y'][0].value == 'y1'

    assert form.fields['z'] == ''
    assert not form.inputs['z'][0].checked
    assert form.inputs['z'][0].value == 'z1'


def _test_checkbox(form_num, field_num, value, expected_return):

    def _checkbox():
        boxes = browser.document.forms[form_num]['input[type=checkbox]']
        return boxes[field_num]

    def set_checked():
        _checkbox().checked = value

    def set_checked_bool():
        _checkbox().checked = bool(value)

    def click():
        _checkbox().click()

    for strategy in (set_checked, set_checked_bool, click):
        browser.open('/form/checkboxes')
        strategy()
        fieldname = _checkbox().name
        browser.document.forms[form_num]['input[type=submit]'][0].click()
        data = loads(browser.document['#data'].text_content)
        if expected_return:
            assert [fieldname, expected_return] in data
        else:
            assert fieldname not in dict(data).keys()


def _test_checkbox_container_assignment(form_num, fieldname, value,
                                        expected_return):

    def assign_to_field():
        form = browser.document.forms[form_num]
        # fields[fieldname] can be a set-like CheckboxGroup & set with a seq
        form.fields[fieldname] = value

    def fill():
        browser.document.forms[form_num].fill({fieldname: value})

    for strategy in (assign_to_field, fill):
        browser.open('/form/checkboxes')
        strategy()
        browser.document.forms[form_num]['input[type=submit]'][0].click()
        data = loads(browser.document['#data'].text_content)
        if expected_return:
            if isinstance(expected_return, list):
                # ['m1', 'm2']
                for er in expected_return:
                    assert [fieldname, er] in data
            else:
                # 'm1'
                assert [fieldname, expected_return] in data
        else:
            # ''
            assert fieldname not in dict(data).keys()


def test_checkbox_interaction():
    yield _test_checkbox, 1, 0, 'y1', 'y1'
    yield _test_checkbox_container_assignment, 1, 'y', 'y1', 'y1'
    yield _test_checkbox, 1, 1, '', None
    yield _test_checkbox_container_assignment, 1, 'z', '', None

    yield _test_checkbox, 2, 0, 'm1', 'm1'
    yield _test_checkbox_container_assignment, 2, 'm', ['m1'], ['m1']
    yield _test_checkbox_container_assignment, 2, 'm', ['m1', 'm3'], \
          ['m1', 'm3']


def test_basic_radio_state():
    browser.open('/form/radios')
    form = browser.document['form'][0]
    fields = form['input[type=radio]']

    assert not fields[0].checked
    assert not fields[1].checked
    assert not fields[2].checked
    assert fields[3].checked
    assert fields[3].value == 'x4'
    assert form.form_values() == [('x', 'x4')]

    fields[2].checked = True
    assert fields[2].checked
    assert not fields[3].checked
    assert fields[3].value == 'x4'
    assert form.form_values() == [('x', 'x3')]

    fields[3].checked = True
    assert form.form_values() == [('x', 'x4')]

    # can't uncheck a radio box
    fields[3].checked = False
    assert form.form_values() == [('x', 'x4')]

    form.submit(wait_for='page')
    data = loads(browser.document['#data'].text_content)
    assert data == [['x', 'x4']]


def _test_radio(form_num, field_num, value, expected_return):

    def _radio():
        boxes = browser.document.forms[form_num]['input[type=radio]']
        return boxes[field_num]

    def set_checked():
        _radio().checked = value

    def set_checked_bool():
        _radio().checked = bool(value)

    def click():
        _radio().click()

    def assign_to_field():
        form = browser.document.forms[form_num]
        form.fields[fieldname] = value

    def fill():
        browser.document.forms[form_num].fill({fieldname: value})

    for strategy in (set_checked, set_checked_bool, click):
        browser.open('/form/radios')
        strategy()
        fieldname = _radio().name
        browser.document.forms[form_num]['input[type=submit]'][0].click()
        data = loads(browser.document['#data'].text_content)
        if expected_return:
            assert [fieldname, expected_return] in data
        else:
            assert fieldname not in dict(data).keys()


def test_radio_interaction():
    # clears default
    yield _test_radio, 0, 0, 'x1', 'x1'

    # no default
    yield _test_radio, 1, 2, 'm3', 'm3'


@raises(KeyError)
def test_fill_field_not_found():
    browser.open('/form/select')
    browser.document.forms[0].fill({'unexisting': None})


@raises(ValueError)
def test_fill_option_not_found():
    browser.open('/form/select')
    browser.document.forms[0].fill({'sel': 'unexisting'})


def test_fill_ordering():
    browser.open('/form/fill')
    assert browser.document['#data'].text == '[]'
    data = {
        'language': 'espa',
        'derivate': 'lunf',
        'subderivate': 'rosa',
        }
    form = browser.document.forms[0]
    try:
        form.fill(data, wait_for='ajax', timeout=1000)
    except ValueError:
        assert 'javascript' not in browser.capabilities
    else:
        form.submit(wait_for='page')
        args_string = browser.document['#data'].text
        assert 'espa' in args_string
        assert 'lunf' in args_string
        assert 'rosa' in args_string


def test_fill_prefixes_dict():
    browser.open('/form/fill')
    assert browser.document['#data'].text == '[]'
    data = {
        'a': 'abc',
        'xx_b': 'def',
        'boxes': ['1', '3'],
        }
    form = browser.document.forms[1]
    form.fill(data, with_prefix='xx_')
    form.submit(wait_for='page')
    roundtrip = loads(browser.document['#data'].text_content)

    assert sorted(roundtrip) == [
        ['xx_a', 'abc'],
        ['xx_b', 'def'],
        ['xx_boxes', '1'],
        ['xx_boxes', '3'],
        ]


def test_fill_prefixes_sequence():
    browser.open('/form/fill')
    assert browser.document['#data'].text == '[]'
    data = [
        ['xx_a', 'abc'],
        ['boxes', '1'],
        ['b', 'def'],
        ['xx_boxes', '3'],
        ]
    form = browser.document.forms[1]
    form.fill(data, with_prefix='xx_')
    form.submit(wait_for='page')
    roundtrip = loads(browser.document['#data'].text_content)

    assert sorted(roundtrip) == [
        [u'xx_a', u'abc'],
        [u'xx_b', u'def'],
        [u'xx_boxes', u'1'],
        [u'xx_boxes', u'3'],
        ]
