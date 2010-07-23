# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Integration with the 'nose' test runner."""

from __future__ import absolute_import
from logging import getLogger
from optparse import OptionGroup

from nose.plugins.base import Plugin

from alfajor._management import ManagerLookupError, new_manager


logger = getLogger('nose.plugins')


class Alfajor(Plugin):

    name = 'alfajor'
    enabled = True  # FIXME

    def __init__(self):
        Plugin.__init__(self)
        self._contexts = {}

    def options(self, parser, env):
        group = OptionGroup(parser, "Alfajor options")
        group.add_option('-B', '--browser',
                         dest='alfajor_browser_frontend',
                         metavar='ALFAJOR_BROWSER',
                         default=env.get('ALFAJOR_BROWSER'),
                         help='Run functional tests with ALFAJOR_BROWSER '
                         '[ALFAJOR_BROWSER]')
        group.add_option('--alfajor-apiclient',
                         dest='alfajor_apiclient_frontend',
                         metavar='ALFAJOR_BROWSER',
                         default=env.get('ALFAJOR_BROWSER'),
                         help='Run functional tests with ALFAJOR_BROWSER '
                         '[ALFAJOR_BROWSER]')
        group.add_option('--alfajor-config',
                         dest='alfajor_ini_file',
                         metavar='ALFAJOR_CONFIG',
                         default=env.get('ALFAJOR_CONFIG'),
                         help='Specify the name of your configuration file,'
                         'which can be any path on the system. Defaults to'
                         'alfajor.ini'
                         '[ALFAJOR_CONFIG]')
        parser.add_option_group(group)

        group = OptionGroup(parser, "Alfajor Selenium backend options")
        group.add_option('--without-server',
                         dest='alfajor_without_server',
                         metavar='WITHOUT_SERVER',
                         action='store_true',
                         default=env.get('ALFAJOR_WITHOUT_SERVER', False),
                         help='Run functional tests against an already '
                         'running web server rather than start a new server '
                         'process.'
                         '[ALFAJOR_EXTERNAL_SERVER]')
        group.add_option('--server-url',
                         dest='alfajor_server_url',
                         metavar='SERVER_URL',
                         default=env.get('ALFAJOR_SERVER_URL', None),
                         help='Run functional tests against this URL, '
                         'overriding all file-based configuration.'
                         '[ALFAJOR_SERVER_URL]')
        parser.add_option_group(group)

    def configure(self, options, config):
        Plugin.configure(self, options, config)
        alfajor_options = {}
        for key, value in vars(options).iteritems():
            if key.startswith('alfajor_'):
                short = key[len('alfajor_'):]
                alfajor_options[short] = value
        self.options = alfajor_options

    def startContext(self, context):
        try:
            setups = context.__alfajor_setup__
        except AttributeError:
            return
        if not setups:
            return
        managers = set()

        logger.info("Processing alfajor functional browsing for context %r",
                    context.__name__)

        for declaration in setups:
            configuration = declaration.configuration
            logger.info("Enabling alfajor %s in configuration %s",
                        declaration.tool, configuration)

            try:
                manager = new_manager(declaration, self.options, logger)
            except ManagerLookupError, exc:
                logger.warn("Skipping setup of %s in context %r: %r",
                            declaration.tool, context, exc.args[0])
                continue
            managers.add((manager, declaration))
            declaration.proxy._factory = manager.create
        if managers:
            self._contexts[context] = managers

    def stopContext(self, context):
        if context not in self._contexts:
            return
        managers = self._contexts.pop(context)
        for manager, declaration in managers:
            manager.destroy()
            declaration.proxy._instance = None
            declaration.proxy._factory = None
