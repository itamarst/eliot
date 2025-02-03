"""
Tests for L{eliot.json}.
"""

from unittest import TestCase, skipUnless, skipIf
from json import loads
import sys

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
            np.str_("hello"),
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

    def test_basic_types(self):
        """Test serialization of basic Python types."""
        from pathlib import Path
        from datetime import datetime, date, time
        from uuid import UUID
        from collections import defaultdict, OrderedDict, Counter
        from enum import Enum
        
        class TestEnum(Enum):
            A = 1
            B = "test"

        test_data = {
            "path": Path("/tmp/test"),
            "datetime": datetime(2024, 1, 1, 12, 0),
            "date": date(2024, 1, 1),
            "time": time(12, 0),
            "uuid": UUID("12345678-1234-5678-1234-567812345678"),
            "set": {1, 2, 3},
            "defaultdict": defaultdict(list, {"a": [1, 2]}),
            "ordered_dict": OrderedDict([("a", 1), ("b", 2)]),
            "counter": Counter(["a", "a", "b"]),
            "complex": 1 + 2j,
            "enum": TestEnum.A
        }

        serialized = loads(dumps(test_data, default=json_default))
        
        self.assertEqual(serialized["path"], "/tmp/test")
        self.assertEqual(serialized["datetime"], "2024-01-01T12:00:00")
        self.assertEqual(serialized["date"], "2024-01-01")
        self.assertEqual(serialized["time"], "12:00:00")
        self.assertEqual(serialized["uuid"], "12345678-1234-5678-1234-567812345678")
        self.assertEqual(serialized["set"], [1, 2, 3])
        self.assertEqual(serialized["defaultdict"], {"a": [1, 2]})
        self.assertEqual(serialized["ordered_dict"], {"a": 1, "b": 2})
        self.assertEqual(serialized["counter"], {"a": 2, "b": 1})
        self.assertEqual(serialized["complex"], {"real": 1.0, "imag": 2.0})
        self.assertEqual(serialized["enum"], {
            "__enum__": True,
            "name": "A",
            "value": 1,
            "class": "TestEnum"
        })

    @skipUnless(sys.modules.get("pydantic"), "Pydantic not installed.")
    def test_pydantic(self):
        """Test serialization of Pydantic models."""
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            name: str
            value: int

        model = TestModel(name="test", value=42)
        serialized = loads(dumps(model, default=json_default))
        self.assertEqual(serialized, {"name": "test", "value": 42})

    @skipUnless(sys.modules.get("pandas"), "Pandas not installed.")
    def test_pandas(self):
        """Test serialization of Pandas objects."""
        import pandas as pd
        
        # Test Timestamp
        ts = pd.Timestamp('2024-01-01 12:00:00')
        self.assertEqual(loads(dumps(ts, default=json_default)), "2024-01-01T12:00:00")
        
        # Test Series
        series = pd.Series([1, 2, 3])
        self.assertEqual(loads(dumps(series, default=json_default)), [1, 2, 3])
        
        # Test DataFrame
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        self.assertEqual(
            loads(dumps(df, default=json_default)),
            [{'a': 1, 'b': 3}, {'a': 2, 'b': 4}]
        )
        
        # Test Interval
        interval = pd.Interval(0, 1, closed='both')
        self.assertEqual(
            loads(dumps(interval, default=json_default)),
            {'left': 0, 'right': 1, 'closed': 'both'}
        )
        
        # Test Period
        period = pd.Period('2024-01')
        self.assertEqual(loads(dumps(period, default=json_default)), "2024-01")

    @skipUnless(sys.modules.get("polars"), "Polars not installed.")
    def test_polars(self):
        """Test serialization of Polars objects."""
        import polars as pl
        
        # Test Series
        series = pl.Series("a", [1, 2, 3])
        self.assertEqual(loads(dumps(series, default=json_default)), [1, 2, 3])
        
        # Test DataFrame
        df = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
        self.assertEqual(
            loads(dumps(df, default=json_default)),
            [{"a": 1, "b": 3}, {"a": 2, "b": 4}]
        )

    def test_dataclass(self):
        """Test serialization of dataclasses."""
        from dataclasses import dataclass
        
        @dataclass
        class TestDataClass:
            name: str
            value: int

        obj = TestDataClass(name="test", value=42)
        serialized = loads(dumps(obj, default=json_default))
        self.assertEqual(serialized, {"name": "test", "value": 42})
