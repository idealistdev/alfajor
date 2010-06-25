# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Utilities useful for managing functional browsers and HTTP clients."""

import inspect
import sys
import time

__all__ = ['ServerSubProcess', 'eval_dotted_path', 'invoke']


def _import(module_name):
    """Import a module by name."""
    local_name = module_name.split('.')[-1]
    return __import__(module_name, {}, {}, local_name)


def _import_some(dotted_path):
    """Import as much of dotted.path as possible, returning module and
    remainder."""
    steps = list(dotted_path.split('.'))
    modname = [steps.pop(0)]
    mod = _import(modname[0])
    while steps:
        try:
            mod = _import('.'.join(modname + steps[:1]))
        except ImportError:
            break
        else:
            modname.append(steps.pop(0))
    return mod, '.'.join(steps)


def eval_dotted_path(string):
    """module.member.member or module.module:evaled.in.module"""

    if ':' not in string:
        mod, expr = _import_some(string)
    else:
        modname, expr = string.split(':', 1)
        mod = _import(modname)
    if expr:
        return eval(expr, mod.__dict__)
    else:
        return mod


class lazy_property(object):
    """An efficient, memoized @property."""

    def __init__(self, fn):
        self.fn = fn
        self.__name__ = fn.func_name
        self.__doc__ = fn.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        obj.__dict__[self.__name__] = result = self.fn(obj)
        return result


def to_pairs(dictlike):
    """Yield (key, value) pairs from any dict-like object.

    Implements an optimized version of the dict.update() definition of
    "dictlike".

    """
    if hasattr(dictlike, 'items'):
        return dictlike.items()
    elif hasattr(dictlike, 'keys'):
        return [(key, dictlike[key]) for key in dictlike.keys()]
    else:
        return [(key, value) for key, value in dictlike]


def _optargs_to_kwargs(args):
    """Convert --bar-baz=quux --xyzzy --no-squiz to kwargs-compatible pairs.

    E.g., [('bar_baz', 'quux'), ('xyzzy', True), ('squiz', False)]

    """
    kwargs = []
    for arg in args:
        if not arg.startswith('--'):
            raise RuntimeError("Unknown option %r" % arg)
        elif '=' in arg:
            key, value = arg.split('=', 1)
            key = key[2:].replace('-', '_')
            if value.isdigit():
                value = int(value)
        elif arg.startswith('--no-'):
            key, value = arg[5:].replace('-', '_'), False
        else:
            key, value = arg[2:].replace('-', '_'), True
        kwargs.append((key, value))
    return kwargs


def invoke():
    """Load and execute a Python function from the command line.

    Functions may be specified in dotted-path/eval syntax, in which case the
    expression should evaluate to a callable function:

       module.name:pythoncode.to.eval

    Or by module name alone, in which case the function 'main' is invoked in
    the named module.

       module.name

    If configuration files are provided, they will be read and all items from
    [defaults] will be passed to the function as keyword arguments.

    """
    def croak(msg):
        print >> sys.stderr, msg
        sys.exit(1)
    usage = "Usage: %s module.name OR module:callable"

    target, args = None, []
    try:
        for arg in sys.argv[1:]:
            if arg.startswith('-'):
                args.append(arg)
            else:
                if target:
                    raise RuntimeError
                target = arg
        if not target:
            raise RuntimeError
    except RuntimeError:
        croak(usage + "\n" + inspect.cleandoc(invoke.__doc__))
    clean = _optargs_to_kwargs(args)
    kwargs = dict(clean)

    try:
        hook = eval_dotted_path(target)
    except (NameError, ImportError), exc:
        croak("Could not invoke %r: %r" % (target, exc))

    if isinstance(hook, type(sys)) and hasattr(hook, 'main'):
        hook = hook.main
    if not callable(hook):
        croak("Entrypoint %r is not a callable function or "
              "module with a main() function.")

    retval = hook(**kwargs)
    sys.exit(retval)


class ServerSubProcess(object):
    """Starts and stops subprocesses."""

    def __init__(self, cmd, ping=None):
        self.cmd = cmd
        self.process = None
        if not ping:
            self.host = self.port = None
        else:
            if ':' in ping:
                self.host, port = ping.split(':', 1)
                self.port = int(port)
            else:
                self.host = ping
                self.port = 80

    def start(self):
        """Start the process."""
        import shlex
        from subprocess import Popen, PIPE, STDOUT

        if self.process:
            raise RuntimeError("Process already started.")
        if self.host and self.network_ping():
            raise RuntimeError("A process is already running on port %s" %
                               self.port)

        if isinstance(self.cmd, basestring):
            cmd = shlex.split(self.cmd)
        else:
            cmd = self.cmd
        process = Popen(cmd, stdout=PIPE, stderr=STDOUT, close_fds=True)

        if not self.host:
            time.sleep(0.35)
            if process.poll():
                output = process.communicate()[0]
                raise RuntimeError("Did not start server!  Woe!\n" + output)
            self.process = process
            return

        start = time.time()
        while process.poll() is None and time.time() - start < 15:
            if self.network_ping():
                break
        else:
            output = process.communicate()[0]
            raise RuntimeError("Did not start server!  Woe!\n" + output)
        self.process = process

    def stop(self):
        """Stop the process."""
        if not self.process:
            return
        try:
            self.process.terminate()
        except AttributeError:
            import os
            import signal
            os.kill(self.process.pid, signal.SIGQUIT)
        for i in xrange(20):
            if self.process.poll() is not None:
                break
            time.sleep(0.1)
        else:
            try:
                self.process.kill()
            except AttributeError:
                import os
                os.kill(self.process.pid, signal.SIGKILL)
        self.process = None

    def network_ping(self):
        """Return True if the :attr:`host` accepts connects on :attr:`port`."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.host, self.port))
            sock.shutdown(socket.SHUT_RDWR)
        except (IOError, socket.error):
            return False
        else:
            return True
        finally:
            del sock
