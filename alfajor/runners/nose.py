# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Integration with the 'nose' test runner."""

from __future__ import absolute_import
from base64 import b64decode
from logging import getLogger
from optparse import OptionGroup
from os import path

from nose.plugins.base import Plugin

from alfajor._management import ManagerLookupError, new_manager


logger = getLogger('nose.plugins')


class Alfajor(Plugin):

    name = 'alfajor'
    enabled = True  # FIXME
    alfajor_enabled_screenshot = False

    def __init__(self):
        Plugin.__init__(self)
        self._contexts = []

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

        group = OptionGroup(parser, "Alfajor Screenshot Options")
        group.add_option(
            "--screenshot", action="store_true",
            dest="alfajor_enabled_screenshot",
            default=env.get('ALFAJOR_SCREENSHOT', False),
            help="Take screenshots of failed pages")
        group.add_option(
            "--screenshot-dir",
            dest="alfajor_screenshot_dir",
            default=env.get('ALFAJOR_SCREENSHOT_DIR', ''),
            help="Dir to store screenshots")
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
            self._contexts.append((context, managers))

    def stopContext(self, context):
        # self._contexts is a list of tuples, [0] is the context key
        if self._contexts and context == self._contexts[-1][0]:
            key, managers = self._contexts.pop(-1)
            for manager, declaration in managers:
                manager.destroy()
                declaration.proxy._instance = None
                declaration.proxy._factory = None

    def addError(self, test, err):
        self.screenshotIfEnabled(test)

    def addFailure(self, test, err):
        self.screenshotIfEnabled(test)

    def screenshotIfEnabled(self, test):
        if self.options['enabled_screenshot']:
            selenium = self._getSelenium()
            if selenium:
                self.screenshot(selenium, test)

    def _getSelenium(self):
        """Get the selenium instance for this test if one exists.

        Otherwise return None.
        """
        assert self._contexts
        contexts, managers = self._contexts[-1]
        for manager, declaration in managers:
            instance = declaration.proxy._instance
            if hasattr(instance, 'selenium'):
                return instance.selenium
        return None

    def screenshot(self, selenium, test):
        img = selenium.capture_entire_page_screenshot_to_string()
        test_name = test.id().split('.')[-1]
        directory = self.options['screenshot_dir']
        output_file = open('/'.join(
                [path.abspath(directory), test_name + '.png']), "w")
        output_file.write(b64decode(img))
        output_file.close()
