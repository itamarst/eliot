"""
Utilities that don't go anywhere else.
"""

from __future__ import unicode_literals

import sys
from types import ModuleType

from six import exec_, text_type as unicode, PY3
from boltons.functools import wraps


def safeunicode(o):
    """
    Like C{unicode()}, but catches and swallows any raised exceptions.

    @param o: An object of some sort.

    @return: C{unicode(o)}, or an error message if that failed.
    @rtype: C{unicode}
    """
    try:
        return unicode(o)
    except:
        # Not much we can do about this...
        return "eliot: unknown, unicode() raised exception"


def saferepr(o):
    """
    Like C{unicode(repr())}, but catches and swallows any raised exceptions.

    @param o: An object of some sort.

    @return: C{unicode(repr(o))}, or an error message if that failed.
    @rtype: C{unicode}
    """
    try:
        return unicode(repr(o))
    except:
        # Not much we can do about this...
        return "eliot: unknown, unicode() raised exception"


def load_module(name, original_module):
    """
    Load a copy of a module, distinct from what you'd get if you imported
    it directly.

    @param str name: The name of the new module.
    @param original_module: The original module we're recreating.

    @return: A new, distinct module.
    """
    module = ModuleType(name)
    if PY3:
        import importlib.util

        spec = importlib.util.find_spec(original_module.__name__)
        source = spec.loader.get_code(original_module.__name__)
    else:
        if getattr(sys, "frozen", False):
            raise NotImplementedError("Can't load modules on Python 2 with PyInstaller")
        path = original_module.__file__
        if path.endswith(".pyc") or path.endswith(".pyo"):
            path = path[:-1]
        with open(path) as f:
            source = f.read()
    exec_(source, module.__dict__, module.__dict__)
    return module


def exclusively(f):
    """
    Decorate a function to make it thread-safe by serializing invocations
    using a per-instance lock.
    """

    @wraps(f)
    def exclusively_f(self, *a, **kw):
        with self._lock:
            return f(self, *a, **kw)

    return exclusively_f
