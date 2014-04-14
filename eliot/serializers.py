"""
Standardized serialization code.
"""

from __future__ import unicode_literals

from hashlib import md5

_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def timestamp(dt):
    """
    Convert a UTC datetime to a string.

    @param dt: A C{datetime.datetime} in UTC timezone.

    @return: C{unicode}
    """
    return dt.strftime(_TIME_FORMAT)



def identity(value):
    """
    Return the passed in object.
    """
    return value



def md5hex(data):
    """
    Return hex MD5 of the input bytes.

    @param data: Some C{bytes}.

    @return: Hex-encoded MD5 of the data.
    """
    return md5(data).hexdigest()
