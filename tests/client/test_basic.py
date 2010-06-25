# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

from tests.client import client


def test_simple_json_fetch():
    response = client.get('/json_data')
    assert response.is_json
    assert response.json['test'] == 'data'
