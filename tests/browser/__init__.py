# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

import os

from alfajor import WebBrowser

from nose.tools import with_setup

browser = WebBrowser()
browser.configure_in_scope('self-tests')


def setup_fn():
    pass


def teardown_fn():
    browser.reset()


def browser_test():
    def dec(fn):
        return with_setup(setup_fn, teardown_fn)(fn)
    return dec

browser_test.__test__ = False


def screenshot_fails(file):
    def dec(fn):
        def test(*args, **kw):
            try:
                fn(*args, **kw)
            except:
                if os.path.exists(file):
                    os.remove(file)
                    return True
                else:
                    return False
        test.__name__ = fn.__name__
        return test
    return dec
