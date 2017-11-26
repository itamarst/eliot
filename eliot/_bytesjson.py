"""
Python 2/3 JSON encoding/decoding, emulating Python 2's json module.

Python 3 json module doesn't support decoding bytes or encoding. Rather than
adding isinstance checks in main code path which would slow down Python 2,
instead we write our encoder that can support those.
"""

import json as pyjson

from six import PY2


def _loads(s):
    """
    Support decoding bytes.
    """
    if isinstance(s, bytes):
        s = s.decode("utf-8")
    return pyjson.loads(s)


def _dumps(obj, cls=pyjson.JSONEncoder):
    """
    Encode to bytes, and presume bytes in inputs are UTF-8 encoded strings.
    """
    class WithBytes(cls):
        """
        JSON encoder that supports L{bytes}.
        """
        def default(self, o):
            if isinstance(o, bytes):
                return o.decode("utf-8")
            return cls.default(self, o)

    return pyjson.dumps(obj, cls=WithBytes).encode("utf-8")


if PY2:
    # No need for the above on Python 2
    loads, dumps = pyjson.loads, pyjson.dumps
else:
    loads, dumps = _loads, _dumps

__all__ = ["loads", "dumps"]
