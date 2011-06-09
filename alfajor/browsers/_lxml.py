# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.


"""Low level LXML element implementation & parser wrangling."""
from collections import defaultdict
import mimetypes
import re
from UserDict import DictMixin
from textwrap import fill

from lxml import html as lxml_html
from lxml.etree import ElementTree, XPath
from lxml.html import (
    fromstring as html_from_string,
    tostring,
    )
from lxml.html._setmixin import SetMixin

from alfajor._compat import property
from alfajor.utilities import lazy_property, to_pairs


__all__ = ['html_parser_for', 'html_from_string']
_single_id_selector = re.compile(r'#[A-Za-z][A-Za-z0-9:_.\-]*$')
XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"

# lifted from lxml
_options_xpath = XPath(
    "descendant-or-self::option|descendant-or-self::x:option",
    namespaces={'x': XHTML_NAMESPACE})
_collect_string_content = XPath("string()")
_forms_xpath = XPath("descendant-or-self::form|descendant-or-self::x:form",
                     namespaces={'x': XHTML_NAMESPACE})


def _nons(tag):
    if isinstance(tag, basestring):
        if (tag[0] == '{' and
            tag[1:len(XHTML_NAMESPACE) + 1] == XHTML_NAMESPACE):
            return tag.split('}')[-1]
    return tag

# not lifted from lxml
_enclosing_form_xpath = XPath('ancestor::form[1]')


class callable_unicode(unicode):
    """Compatibility class for 'element.text_content'"""

    def __call__(self):
        return unicode(self)


def html_parser_for(browser, element_mixins):
    "Return an HTMLParser linked to *browser* and powered by *element_mixins*."
    parser = lxml_html.HTMLParser()
    parser.set_element_class_lookup(ElementLookup(browser, element_mixins))
    return parser


class DOMMixin(object):
    """Supplies DOM parsing and query methods to browsers.

    Browsers must implement a ``self._lxml_parser`` property that contains a
    parser specific to this browser instance.  For example:

      element_mixins = {} # pairs of 'element name': <mixin class>

      @lazy_property
      def _lxml_parser(self):
          return html_parser_for(self, self.element_mixins)

    """

    @lazy_property
    def document(self):
        """An LXML tree of the :attr:`response` content."""
        # TODO: document decision to use 'fromstring' (means dom may
        # be what the remote sent, may not.)
        if self.response is None:
            return None
        return html_from_string(self.response, parser=self._lxml_parser)

    def sync_document(self):
        """Synchronize the :attr:`document` DOM with the visible page."""
        self.__dict__.pop('document', None)

    def __contains__(self, needle):
        """True if *needle* exists anywhere in the response content."""
        # TODO: make this normalize whitespace?  something like split
        # *needle* on whitespace, build a regex of r'\s+'-separated
        # bits.  this could be a fallback to a simple containment
        # test.
        document = self.document
        if document is None:
            return False
        return needle in document.text_content

    @property
    def xpath(self):
        """An xpath querying function querying at the top of the document."""
        return self.document.xpath

    @property
    def cssselect(self):
        """A CSS selector function selecting at the top of the document."""
        return self.document.cssselect


class DOMElement(object):
    """Functionality added to all elements on all browsers."""

    @lazy_property
    def fq_xpath(self):
        """The fully qualified xpath to this element."""
        return ElementTree(self).getpath(self)

    @property
    def forms(self):
        """Return a list of all the forms."""
        return _FormsList(_forms_xpath(self))

    # DOM methods (Mostly applicable only with javascript enabled.)  Capable
    # browsers should re-implement these methods.

    def click(self, wait_for=None, timeout=0):
        """Click this element."""

    def double_click(self, wait_for=None, timeout=0):
        """Double-click this element."""

    def mouse_over(self, wait_for=None, timeout=0):
        """Move the mouse into this element's bounding box."""

    def mouse_out(self, wait_for=None, timeout=0):
        """Move the mouse out of this element's bounding box."""

    def focus(self, wait_for=None, timeout=0):
        """Shift focus to this element."""

    def fire_event(self, name, wait_for=None, timeout=0):
        """Fire DOM event *name* on this element."""

    # TODO:jek: investigate css-tools for implementing this for the WSGI
    # browser
    is_visible = True
    """True if the element is visible.

    Note: currently always True in the WSGI browser.

    """

    @property
    def text_content(self):
        """The text content of the tag and its children.

        This property overrides the text_content() method of regular
        lxml.html elements.  Similar, but acts usable as an
        attribute or as a method call and normalizes all whitespace
        as single spaces.

        """
        text = u' '.join(_collect_string_content(self).split())
        return callable_unicode(text)

    @property
    def innerHTML(self):
        inner = ''.join(tostring(el) for el in self.iterchildren())
        if self.text:
            return self.text + inner
        else:
            return inner

    def __contains__(self, needle):
        """True if the element or its children contains *needle*.

        :param needle: may be an document element, integer index or a
        CSS select query.

        If *needle* is a document element, only immediate decedent
        elements are considered.

        """
        if not isinstance(needle, (int, basestring)):
            return super(DOMElement, self).__contains__(needle)
        try:
            self[needle]
        except (AssertionError, IndexError):
            return False
        else:
            return True

    def __getitem__(self, key):
        """Retrieve elements by integer index, id or CSS select query."""
        if not isinstance(key, basestring):
            return super(DOMElement, self).__getitem__(key)
        # '#foo'?  (and not '#foo li')
        if _single_id_selector.match(key):
            try:
                return self.get_element_by_id(key[1:])
            except KeyError:
                label = 'Document' if self.tag == 'html' else 'Fragment'
                raise AssertionError("%s contains no element with "
                                     "id %r" % (label, key))
        # 'li #foo'?  (and not 'li #foo li')
        elif _single_id_selector.search(key):
            elements = self.cssselect(key)
            if len(elements) != 1:
                label = 'Document' if self.tag == 'html' else 'Fragment'
                raise AssertionError("%s contains %s elements matching "
                                     "id %s!" % (label, len(elements), key))
            return elements[0]
        else:
            elements = self.cssselect(key)
            if not elements:
                label = 'Document' if self.tag == 'html' else 'Fragment'
                raise AssertionError("%s contains no elements matching "
                                     "css selector %r" % (label, key))
            return elements

    def __str__(self):
        """An excerpt of the HTML of this element (without its children)."""
        clone = self.makeelement(self.tag, self.attrib, self.nsmap)
        if self.text_content:
            clone.text = u'...'
        value = self.get('value', '')
        if len(value) > 32:
            clone.attrib['value'] = value + u'...'
        html = tostring(clone)
        return fill(html, 79, subsequent_indent='    ')


class FormElement(object):

    @property
    def inputs(self):
        """An accessor for all the input elements in the form.

        See :class:`InputGetter` for more information about the object.
        """
        return InputGetter(self)

    def fields(self):
        """A dict-like read/write mapping of form field values."""
        return FieldsDict(self.inputs)

    fields = property(fields, lxml_html.FormElement._fields__set)

    def submit(self, wait_for=None, timeout=0):
        """Submit the form's values.

        Equivalent to hitting 'return' in a browser form: the data is
        submitted without the submit button's key/value pair.

        """

    def fill(self, values, wait_for=None, timeout=0, with_prefix=u''):
        """Fill fields of the form from *values*.

        :param values: a mapping or sequence of name/value pairs of form data.
          If a sequence is provided, the sequence order will be respected when
          filling fields with the exception of disjoint pairs in a checkbox
          group, which will be set all at once.

        :param with_prefix: optional, a string that all form fields should
          start with.  If a supplied field name does not start with this
          prefix, it will be prepended.

        """
        grouped = _group_key_value_pairs(values, with_prefix)
        fields = self.fields
        for name, field_values in grouped:
            if len(field_values) == 1:
                value = field_values[0]
            else:
                value = field_values
            fields[name] = value

    def form_values(self):
        """Return name, value pairs of form data as a browser would submit."""
        results = []
        for name, elements in self.inputs.iteritems():
            if not name:
                continue
            if elements[0].tag == 'input':
                type = elements[0].type
            else:
                type = elements[0].tag
            if type in ('submit', 'image', 'reset'):
                continue
            for el in elements:
                value = el.value
                if getattr(el, 'checkable', False):
                    if not el.checked:
                        continue
                    # emulate browser behavior for valueless checkboxes
                    results.append((name, value or 'on'))
                    continue
                elif type == 'select':
                    if value is None:
                        # this won't be reached unless the first option is
                        # <option/>
                        options = el.cssselect('> option')
                        if options:
                            results.append((name, u''))
                        continue
                    elif el.multiple:
                        for v in value:
                            results.append((name, v))
                        continue
                elif type == 'file':
                    if value:
                        mimetype = mimetypes.guess_type(value)[0] \
                                or 'application/octet-stream'
                        results.append((name, (value, mimetype)))
                        continue
                results.append((name, value or u''))
        return results

    def __str__(self):
        """The HTML of this element and a dump of its fields."""
        lines = [DOMElement.__str__(self).rstrip('</form>').rstrip('...')]
        fields = self.fields
        for field_name in sorted(fields.keys()):
            lines.append('* %s = %s' % (field_name, fields[field_name]))
        return '\n'.join(lines)


class _InputControl(object):
    """Common functionality for all interactive form elements."""

    @property
    def form(self):
        """The enclosing <form> tag for this field."""
        try:
            return _enclosing_form_xpath(self)[0]
        except IndexError:
            return None


def _value_from_option(option):
    """
    Pulls the value out of an option element, following order rules of value
    attribute, text and finally empty string.
    """
    opt_value = option.get('value')
    if opt_value is None:
        opt_value = option.text or u''
    if opt_value:
        opt_value = opt_value.strip()
    return opt_value


# More or less from
class MultipleSelectOptions(SetMixin):
    """
    Represents all the selected options in a ``<select multiple>`` element.

    You can add to this set-like option to select an option, or remove
    to unselect the option.
    """

    def __init__(self, select):
        self.select = select

    def options(self):
        """
        Iterator of all the ``<option>`` elements.
        """
        return iter(_options_xpath(self.select))
    options = property(options)

    def __iter__(self):
        for option in self.options:
            if 'selected' in option.attrib:
                yield _value_from_option(option)

    def add(self, item):
        for option in self.options:
            opt_value = _value_from_option(option)
            if opt_value == item:
                option.set('selected', '')
                break
        else:
            raise ValueError(
                "There is no option with the value %r" % item)

    def remove(self, item):
        for option in self.options:
            opt_value = _value_from_option(option)
            if opt_value == item:
                if 'selected' in option.attrib:
                    del option.attrib['selected']
                else:
                    raise ValueError(
                        "The option %r is not currently selected" % item)
                break
        else:
            raise ValueError(
                "There is not option with the value %r" % item)

    def __repr__(self):
        return '<%s {%s} for select name=%r>' % (
            self.__class__.__name__,
            ', '.join([repr(v) for v in self]),
            self.select.name)


# Patched from lxml
class SelectElement(_InputControl):
    """
    ``<select>`` element.  You can get the name with ``.name``.

    ``.value`` will be the value of the selected option, unless this
    is a multi-select element (``<select multiple>``), in which case
    it will be a set-like object.  In either case ``.value_options``
    gives the possible values.

    The boolean attribute ``.multiple`` shows if this is a
    multi-select.
    """

    def _value__get(self):
        """
        Get/set the value of this select (the selected option).

        If this is a multi-select, this is a set-like object that
        represents all the selected options.
        """
        if self.multiple:
            return MultipleSelectOptions(self)
        for el in _options_xpath(self):
            if el.get('selected') is not None:
                return _value_from_option(el)
        return None

    def _value__set(self, value):
        if self.multiple:
            if isinstance(value, basestring):
                raise TypeError(
                    "You must pass in a sequence")
            self.value.clear()
            self.value.update(value)
            return
        if value is not None:
            value = value.strip()
            for el in _options_xpath(self):
                opt_value = _value_from_option(el)
                if opt_value == value:
                    checked_option = el
                    break
            else:
                raise ValueError(
                    "There is no option with the value of %r" % value)
        for el in _options_xpath(self):
            if 'selected' in el.attrib:
                del el.attrib['selected']
        if value is not None:
            checked_option.set('selected', '')

    def _value__del(self):
        # FIXME: should del be allowed at all?
        if self.multiple:
            self.value.clear()
        else:
            self.value = None

    value = property(_value__get, _value__set, _value__del, doc=_value__get.__doc__)

    def value_options(self):
        """
        All the possible values this select can have (the ``value``
        attribute of all the ``<option>`` elements.
        """
        options = []
        for el in _options_xpath(self):
            options.append(_value_from_option(el))
        return options
    value_options = property(value_options, doc=value_options.__doc__)

    def _multiple__get(self):
        """
        Boolean attribute: is there a ``multiple`` attribute on this element.
        """
        return 'multiple' in self.attrib
    def _multiple__set(self, value):
        if value:
            self.set('multiple', '')
        elif 'multiple' in self.attrib:
            del self.attrib['multiple']
    multiple = property(_multiple__get, _multiple__set, doc=_multiple__get.__doc__)


def _append_text_value(existing, new, allow_multiline):
    buffer = list(existing)
    for char in new:
        val = ord(char)
        # a printable char?
        if val > 31:
            buffer.append(char)
        elif allow_multiline and val in (10, 13):
            buffer.append(char)
        elif val == 127:
            raise NotImplementedError("delete? seriously?")
        # backspace
        elif val == 8:
            if buffer[-2:] == ['\r', '\n']:
                del buffer[-2:]
            else:
                del buffer[-1:]
    return ''.join(buffer)


class InputElement(_InputControl):

    def enter(self, text):
        """Append *text* into the value of the input field."""
        if self.type not in ('text', 'radio'):
            raise TypeError('Can not type into <input type=%s>' % self.type)
        self.value = _append_text_value(self.value, text, False)

    @property
    def checked(self):
        if not self.checkable:
            raise AttributeError("Not a checkable input type")
        return 'checked' in self.attrib

    @checked.setter
    def checked(self, value):
        if not self.checkable:
            raise AttributeError("Not a checkable input type")
        have = 'checked' in self.attrib
        if (value and have) or (not value and not have):
            return
        if self.type == 'radio':
            # You can't un-check a radio button in any browser I know of
            if have and not value:
                return
            for el in self.form.inputs[self.name]:
                if el.value == self.value:
                    el.set('checked', '')
                else:
                    el.attrib.pop('checked', None)
            return
        if value:
            self.set('checked', '')
        elif have:
            del self.attrib['checked']


class TextareaElement(_InputControl):

    def enter(self, text):
        """Append *text* into the value of the field."""
        self.value = _append_text_value(self.value, text, True)


class ButtonElement(_InputControl):
    pass


base_elements = {
    '*': DOMElement,
    'button': ButtonElement,
    'form': FormElement,
    'input': InputElement,
    'select': SelectElement,
    'textarea': TextareaElement,
    }


class ElementLookup(lxml_html.HtmlElementClassLookup):

    # derived from the lxml class

    def __init__(self, browser, mixins):
        lxml_html.HtmlElementClassLookup.__init__(self)
        mixins = list(to_pairs(mixins))

        mix_all = tuple(cls for name, cls in mixins if name == '*')

        for name in ('HtmlElement', 'HtmlComment', 'HtmlProcessingInstruction',
                     'HtmlEntity'):
            base = getattr(lxml_html, name)
            mixed = type(name,  mix_all + base.__bases__, {'browser': browser})
            setattr(self, name, mixed)

        classes = self._element_classes
        mixers = {}
        for name, value in mixins:
            if name == '*':
                continue
            mixers.setdefault(name, []).append(value)

        for name, value in mixins:
            if name != '*':
                continue
            for n in classes.keys():
                mixers.setdefault(n, []).append(value)

        for name, mix_bases in mixers.items():
            cur = classes.get(name, self.HtmlElement)
            bases = tuple(mix_bases + [cur])
            classes[name] = type(cur.__name__, bases, {'browser': browser})
        self._element_classes = classes

    def lookup(self, node_type, document, namespace, name):
        if node_type == 'element':
            return self._element_classes.get(name.lower(), self.HtmlElement)
        elif node_type == 'comment':
            return self.HtmlComment
        elif node_type == 'PI':
            return self.HtmlProcessingInstruction
        elif node_type == 'entity':
            return self.HtmlEntity


class InputGetter(lxml_html.InputGetter):
    """Accesses form elements by name.

    Indexing the object with ``[name]`` will return a list of elements
    having that name.

    This differs from the lxml behavior of this object, which comingles scalar
    and sequence results based on the form element type.

    """

    def __getitem__(self, name):
        results = self._name_xpath(self.form, name=name)
        if not results:
            raise KeyError("No input element with the name %r" % name)
        return results
        # TODO:             group = RadioGroup(results)

    def iteritems(self):
        for name in self.keys():
            yield (name, self[name])


class FieldsDict(DictMixin):
    """Reflects the current state of a form as a browser sees it."""

    # Modeled after lxml_html.FieldsDict

    class CheckableProxy(lxml_html.CheckboxValues):

        def __iter__(self):
            for el in self.group:
                if el.checked:
                    yield el.get('value', 'on')

        def add(self, value):
            for el in self.group:
                if el.get('value', 'on') == value:
                    el.checked = True
                    break
            else:
                raise KeyError("No checkbox with value %r" % value)

        def remove(self, value):
            for el in self.group:
                if el.get('value', 'on') == value:
                    el.checked = False
                    break
            else:
                raise KeyError("No checkbox with value %r" % value)

        def __repr__(self):
            return '<%s {%s} for checkboxes name=%r>' % (
                self.__class__.__name__,
                ', '.join([repr(v) for v in self]),
                self.group[0].name)

    def __init__(self, inputs):
        self.inputs = inputs

    def __getitem__(self, name):
        elements = self.inputs[name]
        first = elements[0]
        checkable = getattr(first, 'checkable', False)

        if len(elements) == 1:
            if checkable:
                return first.value if first.checked else ''
            return first.value
        # repeated <input type="text" name="name"> only report the first
        if not checkable:
            return first.value
        return self.CheckableProxy(elements)

    def __setitem__(self, name, value):
        elements = self.inputs[name]
        first = elements[0]
        checkable = getattr(first, 'checkable', False)

        if len(elements) == 1:
            if not checkable:
                first.value = value
            # checkbox dance
            elif value is True or value == first.value:
                first.checked = True
            elif value is False or value == u'':
                first.checked = False
            else:
                raise ValueError("Expected %r, '', True or False for "
                                 "checkable element %r" % (first.value, name))
        elif not checkable:
            # repeated <input type="text" name="name"> only set the first
            first.value = value
        else:
            proxy = self.CheckableProxy(elements)
            if isinstance(value, basestring):
                proxy.update([value])
            else:
                proxy.update(value)

    def __delitem__(self, name):
        raise KeyError("You cannot remove keys from FieldsDict")

    def keys(self):
        return self.inputs.keys()

    def __contains__(self, name):
        return name in self.inputs


def _group_key_value_pairs(values, with_prefix=''):
    """Transform *values* into a sequence of ('name', ['values']) pairs.

    For use by form.fill().  Collapses repeats of a given name into a single
    list of values.  (And non-repeated names as a list of one value.)

    :param values: a mapping or sequence of name/value pairs.

    :param with_prefix: optional, a string that all form fields should
      start with.  If a supplied field name does not start with this
      prefix, it will be prepended.

    """
    grouped = defaultdict(list)
    transformed_keys = []
    for key, value in to_pairs(values):
        if with_prefix and not key.startswith(with_prefix):
            key = with_prefix + key
        grouped[key].append(value)
        if key not in transformed_keys:
            transformed_keys.append(key)
    return [(key, grouped[key]) for key in transformed_keys]


class _FormsList(list):
    """A printable list of forms present in the document."""

    def __str__(self):
        return "\n".join(map(str, self))
