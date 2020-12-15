"""
Common testing infrastructure.
"""

from io import BytesIO
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

    def __init__(self, argv, stdinBytes):
        """
        @param argv: List of command-line arguments.

        @param stdinBytes: C{bytes} that are readable from stdin.
        """
        self.argv = argv
        self.stdin = BytesIO(stdinBytes)
        self.stdout = BytesIO()
        self.stderr = BytesIO()
