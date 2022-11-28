"""
Tests for L{eliot._util}.
"""


from unittest import TestCase
import pprint

from .._util import load_module


class LoadModuleTests(TestCase):
    """
    Tests for L{load_module}.
    """

    maxDiff = None

    def test_returns_module(self):
        """
        L{load_module} returns an object with same methods as original module.
        """
        loaded = load_module(str("copy"), pprint)
        obj = [1, 2, b"hello"]
        self.assertEqual(loaded.pformat(obj), pprint.pformat(obj))

    def test_name(self):
        """
        L{load_module} returns an object with the given name.
        """
        name = str("my_copy")
        loaded = load_module(name, pprint)
        self.assertEqual(loaded.__name__, name)

    def test_distinct_from_original(self):
        """
        L{load_module} returns a distinct object from the original module.
        """
        loaded = load_module(str("copy"), pprint)
        # Override repr in copy:
        loaded.repr = lambda o: str("OVERRIDE")
        # Demonstrate that override applies to copy but not original:
        self.assertEqual(
            dict(original=pprint.pformat(123), loaded=loaded.pformat(123)),
            dict(original="123", loaded="OVERRIDE"),
        )
