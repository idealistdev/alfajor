# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Compound wait_for expression support."""

__all__ = 'WaitExpression', 'SeleniumWaitExpression'

OR = object()


class WaitExpression(object):
    """Generic wait_for expression generator and compiler.

    Expression objects chain in a jQuery/SQLAlchemy-esque fashion::

      expr = (browser.wait_expression().
              element_present('#druid').
              ajax_complete())

    Or can be configured at instantiation:

      expr = browser.wait_expression(['element_present', '#druid'],
                                     ['ajax_complete'])

    Expression components are and-ed (&&) together.  To or (||), separate
    components with :meth:`or_`::

      element_present('#druid').or_().ajax_complete()

    The expression object can be supplied to any operation which accepts
    a ``wait_for`` argument.

    """

    def __init__(self, *expressions):
        for spec in expressions:
            directive = spec[0]
            args = spec[1:]
            getattr(self, directive)(*args)

    def or_(self):
        """Combine the next expression with an OR instead of default AND."""
        return self

    def element_present(self, finder):
        """True if *finder* is present on the page.

        :param finder: a CSS selector or document element instance

        """
        return self

    def element_not_present(self, expr):
        """True if *finder* is not present on the page.

        :param finder: a CSS selector or document element instance

        """
        return self

    def evaluate_element(self, finder, expr):
        """True if *finder* is present on the page and evaluated by *expr*.

        :param finder: a CSS selector or document element instance

        :param expr: literal JavaScript text; should evaluate to true or
          false.  The variable ``element`` will hold the *finder* DOM element,
          and ``window`` is the current window.

        """
        return self

    def ajax_pending(self):
        """True if jQuery ajax requests are pending."""
        return self

    def ajax_complete(self):
        """True if no jQuery ajax requests are pending."""
        return self

    def __unicode__(self):
        """The rendered value of the expression."""
        return u''


class SeleniumWaitExpression(WaitExpression):
    """Compound wait_for expression compiler for Selenium browsers."""

    def __init__(self, *expressions):
        self._expressions = []
        WaitExpression.__init__(self, *expressions)

    def or_(self):
        self._expressions.append(OR)
        return self

    def element_present(self, finder):
        js = self._is_element_present('element_present', finder, 'true')
        self._expressions.append(js)
        return self

    def element_not_present(self, finder):
        js = self._is_element_present('element_not_present', finder, 'false')
        self._expressions.append(js)
        return self

    def evaluate_element(self, finder, expr):
        locator = to_locator(finder)
        log = evaluation_log('evaluate_element', 'result', locator, expr)
        js = """\
(function () {
  var element;
  try {
    element = selenium.browserbot.findElement('%s');
  } catch (e) {
    element = null;
  };
  var result = false;
  if (element != null)
    result = %s;
  %s
  return result;
})()""" % (js_quote(locator), expr, log)
        self._expressions.append(js)
        return self

    def ajax_pending(self):
        js = """\
(function() {
  var pending = window.jQuery && window.jQuery.active != 0;
  %s
  return pending;
})()""" % predicate_log('ajax_pending', 'complete')
        self._expressions.append(js)
        return self

    def ajax_complete(self):
        js = """\
(function() {
  var complete = window.jQuery ? window.jQuery.active == 0 : true;
  %s
  return complete;
})()""" % predicate_log('ajax_complete', 'complete')
        self._expressions.append(js)
        return self

    def _is_element_present(self, label, finder, result):
        locator = to_locator(finder)
        log = evaluation_log(label, 'found', locator)
        return u"""\
(function () {
  var found = true;
  try {
    selenium.browserbot.findElement('%s');
  } catch (e) {
    found = false;
  };
  %s
  return found == %s;
})()""" % (js_quote(locator), log, result)

    def __unicode__(self):
        last = None
        components = []
        for expr in self._expressions:
            if expr is OR:
                components.append(u'||')
            else:
                if last not in (None, OR):
                    components.append(u'&&')
                components.append(expr)
            last = expr
        predicate = u' '.join(components).replace('\n', ' ')
        return predicate


def js_quote(string):
    """Prepare a string for use in a 'single quoted' JS literal."""
    string = string.replace('\\', r'\\')
    string = string.replace('\'', r'\'')
    return string


def to_locator(expr):
    """Convert a css selector or document element into a selenium locator."""
    if isinstance(expr, basestring):
        return 'css=' + expr
    elif hasattr(expr, '_locator'):
        return expr._locator
    else:
        raise RuntimeError("Unknown page element %r" % expr)


def predicate_log(label, result_variable):
    """Return JS for logging a boolean result test in the Selenium console."""
    js = "LOG.info('wait_for %s ==' + %s);" % (
        js_quote(label), result_variable)
    return js


def evaluation_log(label, result_variable, *args):
    """Return JS for logging an expression eval in the Selenium console."""
    inner = ', '.join(map(js_quote, args))
    js = "LOG.info('wait_for %s(%s)=' + %s);" % (
        js_quote(label), inner, result_variable)
    return js
