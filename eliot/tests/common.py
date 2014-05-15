"""
Common testing infrastructure.
"""

from io import BytesIO


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
