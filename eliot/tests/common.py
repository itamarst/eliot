"""
Common testing infrastructure.
"""

from io import StringIO
from json import JSONEncoder


class CustomObject(object):
    """Gets encoded to JSON."""


class CustomJSONEncoder(JSONEncoder):
    """JSONEncoder that knows about L{CustomObject}."""

    def default(self, o):
        if isinstance(o, CustomObject):
            return "CUSTOM!"
        return JSONEncoder.default(self, o)


class FakeSys(object):
    """
    A fake L{sys} module.
    """

    def __init__(self, argv, stdinStr):
        """
        @param argv: List of command-line arguments.

        @param stdinStr: C{str} that are readable from stdin.
        """
        self.argv = argv
        self.stdin = StringIO(stdinStr)
        self.stdout = StringIO()
        self.stderr = StringIO()
