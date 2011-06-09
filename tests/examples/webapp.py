# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

import os
import tempfile

from werkzeug import Response, Request, Template
from werkzeug.exceptions import NotFound, HTTPException
from werkzeug.routing import Map, Rule


class WebApp(object):

    url_map = Map([
        Rule('/', endpoint='index'),
        Rule('/results', endpoint='results'),
        ])

    def __call__(self, environ, start_response):
        request = Request(environ)
        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
        except NotFound, exc:
            args = {}
        environ['routing_args'] = args
        environ['endpoint'] = endpoint

        try:
            response = self.template_renderer(request)
        except HTTPException, exc:
            # ok, maybe it really was a bogus URL.
            return exc(environ, start_response)
        return response(environ, start_response)


    def template_renderer(self, request):
        endpoint = request.environ['endpoint']
        path = '%s/templates/%s.html' % (
            os.path.dirname(__file__), endpoint)
        try:
            source = open(path).read()
        except IOError:
            raise NotFound()
        template = Template(source)
        handler = getattr(self, endpoint, None)
        context = dict()
        if handler:
            handler(request, context)
        print context
        body = template.render(context)
        return Response(body, mimetype='text/html')

    def results(self, request, context):
        context.update(
            name=request.args.get('name', 'Che'),
        )


def webapp():
    return WebApp()


def run(bind_address='0.0.0.0', port=8009):
    """Run the webapp in a simple server process."""
    from werkzeug import run_simple
    print "* Starting on %s:%s" % (bind_address, port)
    run_simple(bind_address, port, webapp(),
               use_reloader=False, threaded=True)
