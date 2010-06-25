# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""A non-functional web browser.

Documents the canonical base implementation of browsers.  Zero is instantiable
and usable, however it does not supply any capabilities.

"""

from alfajor.utilities import lazy_property
from alfajor.browsers._lxml import DOMMixin, base_elements, html_parser_for
from alfajor.browsers._waitexpr import WaitExpression


__all__ = ['Zero']


class Zero(DOMMixin):
    """A non-functional web browser."""

    capabilities = []

    wait_expression = WaitExpression

    user_agent = {
        'browser': 'zero',
        'platform': 'python',
        'version': '0.1',
        }

    location = '/'

    status_code = 0

    status = None

    response = """\
<html>
  <body>
    <h1>Not Implemented</h>
    <p>Web browsing unavailable.</p>
  </body>
</html>
"""

    def open(self, url, wait_for=None, timeout=0):
        """Navigate to *url*."""

    def reset(self):
        """Reset browser state (clear cookies, etc.)"""

    def wait_for(self, condition, timeout=0):
        """Wait for *condition*."""

    def sync_document(self):
        """The document is always synced."""

    headers = {}
    """A dictionary of HTTP response headers."""

    cookies = {}
    """A dictionary of cookies visible to the current page."""

    def set_cookie(self, name, value, domain=None, path='/', **kw):
        """Set a cookie."""

    def delete_cookie(self, name, domain=None, path='/', **kw):
        """Delete a cookie."""

    @lazy_property
    def _lxml_parser(self):
        return html_parser_for(self, base_elements)

    # ? select_form(...) -> ...

    # future capability:
    #  file upload
