"""
Tests for L{eliot.serializers}.
"""


from unittest import TestCase
from datetime import datetime
from hashlib import md5

from ..serializers import timestamp, identity, md5hex


class SerializerTests(TestCase):
    """
    Tests for standard serializers.
    """

    def test_timestamp(self):
        """
        L{timestamp} converts a UTC L{datetime} to a Unicode strings.
        """
        dt = datetime(2012, 9, 28, 14, 53, 6, 123456)
        self.assertEqual(timestamp(dt), "2012-09-28T14:53:06.123456Z")

    def test_identity(self):
        """
        L{identity} returns the input object.
        """
        obj = object()
        self.assertIs(identity(obj), obj)

    def test_md5hex(self):
        """
        L{md5hex} returns the hex value of a MD5 checksum.
        """
        data = b"01234456789"
        self.assertEqual(md5hex(data), md5(data).hexdigest())
