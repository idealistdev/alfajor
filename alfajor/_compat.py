# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Glue code for Python version compatibility."""

_json = None

try:
    property.getter
except AttributeError:
    class property(property):
        """A work-alike for Python 2.6's property."""
        __slots__ = ()

        def getter(self, fn):
            return property(fn, self.fset, self.fdel)

        def setter(self, fn):
            return property(self.fget, fn, self.fdel)

        def deleter(self, fn):
            return property(self.fget, self.fset, fn)
else:
    property = property


def _load_json():
    global _json
    if _json is None:
        try:
            import json as _json
        except ImportError:
            try:
                import simplejson as _json
            except ImportError:
                pass
        if not _json:
            raise ImportError(
                "This feature requires Python 2.6+ or simplejson.")


def json_loads(*args, **kw):
    if _json is None:
        _load_json()
    return _json.loads(*args, **kw)


def json_dumps(*args, **kw):
    if _json is None:
        _load_json()
    return _json.dumps(*args, **kw)
