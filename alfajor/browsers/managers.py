# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Bridges between test runners and functional browsers."""

from logging import getLogger

from alfajor.utilities import ServerSubProcess, eval_dotted_path


logger = getLogger('alfajor')


def _verify_backend_config(config, required_keys):
    missing = [key for key in required_keys if key not in config]
    if not missing:
        return True
    missing_keys = ', '.join(missing)
    raise RuntimeError("Configuration is missing required keys %s" %
                       missing_keys)


class SeleniumManager(object):
    """TODO

    server_url
    cmd
    ping-address
    selenium-server

    """

    def __init__(self, frontend_name, backend_config, runner_options):
        self.browser_type = frontend_name
        self.config = backend_config
        self.runner_options = runner_options
        self.process = None
        self.browser = None
        self.server_url = self._config('server_url', False)
        if not self.server_url:
            raise RuntimeError("'server_url' is a required configuration "
                               "option for the Selenium backend.")

    def _config(self, key, *default):
        override = self.runner_options.get(key)
        if override:
            return override
        if key in self.config:
            return self.config[key]
        if default:
            return default[0]
        raise LookupError(key)

    def create(self):
        from alfajor.browsers.selenium import Selenium

        base_url = self.server_url
        if (self._config('without_server', False) or
            not self._config('cmd', False)):
            logger.debug("Connecting to existing URL %r", base_url)
        else:
            logger.debug("Starting service....")
            self.process = self.start_subprocess()
            logger.debug("Service started.")
        selenium_server = self._config('selenium-server',
                                       'http://localhost:4444')
        self.browser = Selenium(selenium_server, self.browser_type, base_url)
        return self.browser

    def destroy(self):
        if self.browser and self.browser.selenium._session_id:
            try:
                self.browser.selenium.test_complete()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                pass
        if self.process:
            self.process.stop()
        # avoid irritating __del__ exception on interpreter shutdown
        self.process = None
        self.browser = None

    def start_subprocess(self):
        cmd = self._config('cmd')
        ping = self._config('ping-address', None)

        logger.info("Starting server sub process with %s", cmd)
        process = ServerSubProcess(cmd, ping)
        process.start()
        return process


class WSGIManager(object):
    """Lifecycle manager for global WSGI browsers."""

    def __init__(self, frontend_name, backend_config, runner_options):
        self.config = backend_config

    def create(self):
        from alfajor.browsers.wsgi import WSGI

        entry_point = self.config['server-entry-point']
        app = eval_dotted_path(entry_point)

        base_url = self.config.get('base_url')
        logger.debug("Created in-process WSGI browser.")
        return WSGI(app, base_url)

    def destroy(self):
        logger.debug("Destroying in-process WSGI browser.")


class NetworkManager(object):
    """TODO

    server_url
    cmd
    ping-address

    """

    def __init__(self, frontend_name, backend_config, runner_options):
        self.config = backend_config
        self.runner_options = runner_options
        self.process = None
        self.browser = None
        self.server_url = self._config('server_url', False)
        if not self.server_url:
            raise RuntimeError("'server_url' is a required configuration "
                               "option for the Network backend.")

    def _config(self, key, *default):
        override = self.runner_options.get(key)
        if override:
            return override
        if key in self.config:
            return self.config[key]
        if default:
            return default[0]
        raise LookupError(key)

    def create(self):
        from alfajor.browsers.network import Network

        base_url = self.server_url
        if (self._config('without_server', False) or
            not self._config('cmd', False)):
            logger.debug("Connecting to existing URL %r", base_url)
        else:
            logger.debug("Starting service....")
            self.process = self.start_subprocess()
            logger.debug("Service started.")
        self.browser = Network(base_url)
        return self.browser

    def destroy(self):
        if self.process:
            self.process.stop()
        # avoid irritating __del__ exception on interpreter shutdown
        self.process = None
        self.browser = None

    def start_subprocess(self):
        cmd = self._config('cmd')
        ping = self._config('ping-address', None)

        logger.info("Starting server sub process with %s", cmd)
        process = ServerSubProcess(cmd, ping)
        process.start()
        return process


class ZeroManager(object):
    """Lifecycle manager for global Zero browsers."""

    def __init__(self, frontend_name, backend_config, runner_options):
        pass

    def create(self):
        from alfajor.browsers.zero import Zero
        logger.debug("Creating Zero browser.")
        return Zero()

    def destroy(self):
        logger.debug("Destroying Zero browser.")
