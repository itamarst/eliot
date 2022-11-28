"""
Utilities that don't go anywhere else.
"""

import sys
from types import ModuleType


def safeunicode(o):
    """
    Like C{str()}, but catches and swallows any raised exceptions.

    @param o: An object of some sort.

    @return: C{str(o)}, or an error message if that failed.
    @rtype: C{str}
    """
    try:
        return str(o)
    except:
        # Not much we can do about this...
        return "eliot: unknown, str() raised exception"


def saferepr(o):
    """
    Like C{str(repr())}, but catches and swallows any raised exceptions.

    @param o: An object of some sort.

    @return: C{str(repr(o))}, or an error message if that failed.
    @rtype: C{str}
    """
    try:
        return str(repr(o))
    except:
        # Not much we can do about this...
        return "eliot: unknown, str() raised exception"


def load_module(name, original_module):
    """
    Load a copy of a module, distinct from what you'd get if you imported
    it directly.

    @param str name: The name of the new module.
    @param original_module: The original module we're recreating.

    @return: A new, distinct module.
    """
    import importlib.util

    module = ModuleType(name)
    spec = importlib.util.find_spec(original_module.__name__)
    source = spec.loader.get_code(original_module.__name__)
    exec(source, module.__dict__, module.__dict__)
    return module
