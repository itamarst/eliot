"""
TAI64N encoding and decoding.

TAI64N encodes nanosecond-accuracy timestamps and is supported by logstash.

@see: U{http://cr.yp.to/libtai/tai64.html}.
"""

from __future__ import unicode_literals

import struct
from binascii import b2a_hex, a2b_hex

_STRUCTURE = b">QI"
_OFFSET = (2 ** 62) + 10 # last 10 are leap seconds


def encode(timestamp):
    """
    Convert seconds since epoch to TAI64N string.

    @param timestamp: Seconds since UTC Unix epoch as C{float}.

    @return: TAI64N-encoded time, as C{unicode}.
    """
    seconds = int(timestamp)
    nanoseconds = int((timestamp - seconds) * 1000000000)
    seconds = seconds + _OFFSET
    return "@" + b2a_hex(struct.pack(_STRUCTURE, seconds, nanoseconds))



def decode(tai64n):
    """
    Convert TAI64N string to seconds since epoch.

    Note that dates before 2013 may not decode accurately due to leap second
    issues. If you need correct decoding for earlier dates you can try the
    tai64n package available from PyPI (U{https://pypi.python.org/pypi/tai64n}).

    @param tai64n: TAI64N-encoded time, as C{unicode}.

    @return: Seconds since UTC Unix epoch as C{float}.
    """
    seconds, nanoseconds = struct.unpack(_STRUCTURE, a2b_hex(tai64n[1:]))
    seconds -= _OFFSET
    return seconds + (nanoseconds / 1000000000.0)

