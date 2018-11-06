"""
Tests for L{eliot._json}.
"""

from __future__ import unicode_literals, absolute_import

from unittest import TestCase, skipUnless, skipIf
from json import loads, dumps
import sys

try:
    import numpy as np
except ImportError:
    np = None

from eliot._json import EliotJSONEncoder


class EliotJSONEncoderTests(TestCase):
    """Tests for L{EliotJSONEncoder}."""

    @skipUnless(np, "NumPy not installed.")
    def test_numpy(self):
        """NumPy objects get serialized to readable JSON."""
        l = [np.float32(12.5), np.float64(2.0), np.float16(0.5),
             np.bool(True), np.bool(False), np.bool_(True),
             np.unicode_("hello"),
             np.byte(12), np.short(12), np.intc(-13), np.int_(0),
             np.longlong(100), np.intp(7),
             np.ubyte(12), np.ushort(12), np.uintc(13),
             np.ulonglong(100), np.uintp(7),
             np.int8(1), np.int16(3), np.int32(4), np.int64(5),
             np.uint8(1), np.uint16(3), np.uint32(4), np.uint64(5)]
        l2 = [l, np.array([1, 2, 3])]
        roundtripped = loads(dumps(l2, cls=EliotJSONEncoder))
        self.assertEqual([l, [1, 2, 3]], roundtripped)

    @skipIf(np, "NumPy is installed.")
    def test_numpy_not_imported(self):
        """If NumPy is not available, EliotJSONEncoder continues to work.

        This ensures NumPy isn't a hard dependency.
        """
        with self.assertRaises(TypeError):
            dumps([object()], cls=EliotJSONEncoder)
        self.assertEqual(dumps(12, cls=EliotJSONEncoder), "12")
