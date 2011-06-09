from nose.tools import with_setup
from alfajor import WebBrowser


browser = WebBrowser()
browser.configure_in_scope('examples')

def setup_fn():
    pass

def teardown_fn():
    browser.reset()

def browser_test():
    def dec(fn):
        return with_setup(setup_fn, teardown_fn)(fn)
    return dec

browser_test.__test__ = False
