# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

from alfajor._management import _DeferredProxy

from nose.tools import assert_raises


def test_proxy_readiness():
    class Sentinel(object):
        prop = 123
    sentinel = Sentinel()

    proxy = _DeferredProxy()
    assert_raises(RuntimeError, getattr, proxy, 'prop')

    proxy = _DeferredProxy()
    proxy._factory = lambda: sentinel
    assert proxy.prop == 123
