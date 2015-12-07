"""
Utilities that don't go anywhere else.
"""

from __future__ import unicode_literals

from types import ModuleType

from six import exec_, text_type as unicode


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
    path = original_module.__file__
    if path.endswith(".pyc") or path.endswith(".pyo"):
        path = path[:-1]
    with open(path) as f:
        exec_(f.read(), module.__dict__, module.__dict__)
    return module
