# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Routines for discovering and preparing backend managers."""
import inspect
from logging import getLogger
from os import path

from alfajor.utilities import eval_dotted_path
from alfajor._config import Configuration


__all__ = [
    'APIClient',
    'ManagerLookupError',
    'WebBrowser',
    'new_manager',
    ]

_default_logger = getLogger('alfajor')

managers = {
    'browser': {
        'selenium': 'alfajor.browsers.managers:SeleniumManager',
        'wsgi': 'alfajor.browsers.managers:WSGIManager',
        'zero': 'alfajor.browsers.managers:ZeroManager',
        },
    'apiclient': {
        'wsgi': 'alfajor.apiclient:WSGIClientManager',
        },
    }


try:
    import pkg_resources
except ImportError:
    pass
else:
    for tool in 'browser', 'apiclient':
        group = 'alfajor.' + tool
        for entrypoint in pkg_resources.iter_entry_points(group=group):
            try:
                entry = entrypoint.load()
            except Exception, exc:
                _default_logger.error("Error loading %s: %s", entrypoint, exc)
            else:
                managers[tool][entrypoint.name] = entry


class ManagerLookupError(Exception):
    """Raised if a declaration could not be resolved."""


def new_manager(declaration, runner_options, logger=None):
    try:
        factory = _ManagerFactory(declaration, runner_options, logger)
        return factory.get_instance()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception, exc:
        raise ManagerLookupError(exc)


class _DeferredProxy(object):
    """Fronts for another, created-on-demand instance."""

    def __init__(self):
        self._factory = None
        self._instance = None

    def _get_instance(self):
        if self._instance is not None:  # pragma: nocover
            return self._instance
        if self._factory is None:
            raise RuntimeError("%s is not configured." % type(self).__name__)
        self._instance = instance = self._factory()
        return instance

    def __getattr__(self, key):
        if self._instance is None:
            instance = self._get_instance()
        else:
            instance = self._instance
        return getattr(instance, key)

    def configure_in_scope(self, configuration='default', default_target=None,
                           ini_file=None):
        namespace = inspect.stack()[1][0].f_globals
        setups = namespace.setdefault('__alfajor_setup__', [])
        configuration = Declaration(proxy=self,
                                    configuration=configuration,
                                    default_target=default_target,
                                    ini_file=ini_file,
                                    tool=self.tool,
                                    declared_in=namespace.get('__file__'))
        setups.append(configuration)


class WebBrowser(_DeferredProxy):
    """A web browser for functional tests.

    Acts as a shell around a specific backend browser implementation,
    allowing a browser instance to be imported into a test module's
    namespace before configuration has been processed.

    """
    tool = 'browser'

    def __contains__(self, needle):
        browser = self._get_instance()
        return needle in browser


class APIClient(_DeferredProxy):
    """A wire-level HTTP client for functional tests.

    Acts as a shell around a demand-loaded backend implementation, allowing a
    client instance to be imported into a test module's namespace before
    configuration has been processed.
    """
    tool = 'apiclient'


class Declaration(object):

    def __init__(self, proxy, configuration, default_target, ini_file,
                 tool, declared_in):
        self.proxy = proxy
        self.configuration = configuration
        self.default_target = default_target
        self.ini_file = ini_file
        self.tool = tool
        self.declared_in = declared_in


class _ManagerFactory(object):
    """Encapsulates the process of divining and loading a backend manager."""
    _configs = {}

    def __init__(self, declaration, runner_options, logger=None):
        self.declaration = declaration
        self.runner_options = runner_options
        self.logger = logger or _default_logger
        self.config = self._get_configuration(declaration)
        self.name = declaration.configuration

    def get_instance(self):
        """Return a ready to instantiate backend manager callable.

        Will raise errors if problems are encountered during discovery.

        """
        frontend_name = self._get_frontend_name()
        backend_name = self._get_backend_name(frontend_name)
        tool = self.declaration.tool

        try:
            manager_factory = self._load_backend(tool, backend_name)
        except KeyError:
            raise KeyError("No known backend %r in configuration %r" % (
                backend_name, self.config.source))

        backend_config = self.config.get_section(
            self.name, template='%(name)s+%(tool)s.%(backend)s',
            tool=tool, backend=backend_name,
            logger=self.logger, fallback='default')

        return manager_factory(frontend_name,
                               backend_config,
                               self.runner_options)

    def _get_configuration(self, declaration):
        """Return a Configuration applicable to *declaration*.

        Configuration may come from a declaration option, a runner option
        or the default.

        """
        # --alfajor-config overrides any config data in code
        if self.runner_options['ini_file']:
            finder = self.runner_options['ini_file']
        # if not configured in code, look for 'alfajor.ini' or a declared path
        # relative to the file the declaration was made in.
        else:
            finder = path.abspath(
                path.join(path.dirname(declaration.declared_in),
                          (declaration.ini_file or 'alfajor.ini')))
        # TODO: empty config
        try:
            return self._configs[finder]
        except KeyError:
            config = Configuration(finder)
            self._configs[finder] = config
            return config

    def _get_frontend_name(self):
        """Return the frontend requested by the runner or declaration."""
        runner_override = self.declaration.tool + '_frontend'
        frontend = self.runner_options.get(runner_override)
        if not frontend:
            frontend = self.declaration.default_target
        if not frontend:
            frontend = 'default'
        return frontend

    def _get_backend_name(self, frontend):
        """Return the backend name for *frontend*."""
        if frontend == 'default':
            defaults = self.config.get_section('default-targets', default={})
            key = '%s+%s' % (self.declaration.configuration,
                             self.declaration.tool)
            if key not in defaults:
                key = 'default+%s' % (self.declaration.tool,)
            try:
                frontend = defaults[key]
            except KeyError:
                raise LookupError("No default target declared.")
        mapping = self.config.get_section(self.name, fallback='default')
        try:
            return mapping[frontend]
        except KeyError:
            return mapping['*']

    def _load_backend(self, tool, backend):
        """Load a *backend* callable for *tool*.

        Consults the [tool.backends] section of the active configuration
        first for a "tool = evalable.dotted:path" entry.  If not found,
        looks in the process-wide registry of built-in and pkg_resources
        managed backends.

        A config entry will override an equivalently named process entry.

        """
        point_of_service_managers = self.config.get_section(
            '%(tool)s.backends', default={}, logger=self.logger,
            tool=tool)
        try:
            entry = point_of_service_managers[backend]
        except KeyError:
            pass
        else:
            if callable(entry):
                return entry
            else:
                return eval_dotted_path(entry)

        entry = managers[tool][backend]
        if callable(entry):
            return entry
        fn = eval_dotted_path(entry)
        managers[tool].setdefault(backend, fn)
        return fn
