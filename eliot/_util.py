"""
Utilities that don't go anywhere else.
"""

from __future__ import unicode_literals


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
