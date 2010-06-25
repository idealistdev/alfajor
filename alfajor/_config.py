# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""INI helpers."""
import ConfigParser
from StringIO import StringIO


class Configuration(ConfigParser.SafeConfigParser):
    """Alfajor run-time configuration."""

    _default_config = """\
[default]
wsgi = wsgi
* = selenium

[default+browser.zero]
    """

    def __init__(self, file):
        ConfigParser.SafeConfigParser.__init__(self)
        self.readfp(StringIO(self._default_config))
        if not self.read(file):
            raise IOError("Could not open config file %r" % file)
        self.source = file

    def get_section(self, name, default=None,
                    template='%(name)s', logger=None, fallback=None, **kw):
        section_name = template % dict(kw, name=name)
        try:
            return dict(self.items(section_name))
        except ConfigParser.NoSectionError:
            pass

        msg = "Configuration %r does not contain section %r" % (
            self.source, section_name)

        if fallback and fallback != name:
            try:
                section = self.get_section(fallback, default, template,
                                           logger, **kw)
            except LookupError:
                pass
            else:
                if logger:
                    fallback_name = fallback % dict(kw, name=fallback)
                    logger.debug("%s, falling back to %r" % (
                        msg, section_name, fallback_name))
                return section
        if default is not None:
            if logger:
                    logger.debug(msg + ", using default.")
            return default
        raise LookupError(msg)
