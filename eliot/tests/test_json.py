"""
Tests for L{eliot.json}.
"""

from __future__ import unicode_literals, absolute_import

from unittest import TestCase, skipUnless, skipIf
from math import isnan
from json import loads

try:
    import numpy as np
except ImportError:
    np = None

from eliot.json import (
    EliotJSONEncoder,
    json_default,
    _encoder_to_default_function,
    _dumps_unicode as dumps,
)


class EliotJSONEncoderTests(TestCase):
    """Tests for L{EliotJSONEncoder} and L{json_default}."""

    @skipUnless(np, "NumPy not installed.")
    def test_numpy(self):
        """NumPy objects get serialized to readable JSON."""
        encoder_default = _encoder_to_default_function(EliotJSONEncoder())
        l = [
            np.float32(12.5),
            np.float64(2.0),
            np.float16(0.5),
            np.bool_(True),
            np.unicode_("hello"),
            np.byte(12),
            np.short(12),
            np.intc(-13),
            np.int_(0),
            np.longlong(100),
            np.intp(7),
            np.ubyte(12),
            np.ushort(12),
            np.uintc(13),
            np.ulonglong(100),
            np.uintp(7),
            np.int8(1),
            np.int16(3),
            np.int32(4),
            np.int64(5),
            np.uint8(1),
            np.uint16(3),
            np.uint32(4),
            np.uint64(5),
        ]
        l2 = [l, np.array([1, 2, 3])]
        roundtripped = loads(dumps(l2, default=encoder_default))
        self.assertEqual([l, [1, 2, 3]], roundtripped)
        roundtripped2 = loads(dumps(l2, default=json_default))
        self.assertEqual([l, [1, 2, 3]], roundtripped2)

    @skipIf(np, "NumPy is installed.")
    def test_numpy_not_imported(self):
        """If NumPy is not available, C{json_default} continues to work.

        This ensures NumPy isn't a hard dependency.
        """
        with self.assertRaises(TypeError):
            dumps([object()], default=json_default)
        self.assertEqual(dumps(12, default=json_default), "12")

    @skipUnless(np, "NumPy is not installed.")
    def test_large_numpy_array(self):
        """
        Large NumPy arrays are not serialized completely, since this is (A) a
        performance hit (B) probably a mistake on the user's part.
        """
        a1000 = np.array([0] * 10000)
        self.assertEqual(loads(dumps(a1000, default=json_default)), a1000.tolist())
        a1002 = np.zeros((2, 5001))
        a1002[0][0] = 12
        a1002[0][1] = 13
        a1002[1][1] = 500
        self.assertEqual(
            loads(dumps(a1002, default=json_default)),
            {"array_start": a1002.flat[:10000].tolist(), "original_shape": [2, 5001]},
        )
