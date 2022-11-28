"""
Python 3 JSON encoding/decoding, emulating Python 2's json module.

Python 3 json module doesn't support decoding bytes or encoding. Rather than
adding isinstance checks in main code path which would slow down Python 2,
instead we write our encoder that can support those.
"""

import json as pyjson
import warnings


def loads(s):
    """
    Support decoding bytes.
    """
    if isinstance(s, bytes):
        s = s.decode("utf-8")
    return pyjson.loads(s)


def dumps(obj, cls=pyjson.JSONEncoder):
    """
    Encode to bytes, and presume bytes in inputs are UTF-8 encoded strings.
    """

    class WithBytes(cls):
        """
        JSON encoder that supports L{bytes}.
        """

        def default(self, o):
            if isinstance(o, bytes):
                warnings.warn(
                    "Eliot will soon stop supporting encoding bytes in JSON"
                    " on Python 3",
                    DeprecationWarning,
                )
                return o.decode("utf-8")
            return cls.default(self, o)

    return pyjson.dumps(obj, cls=WithBytes).encode("utf-8")


__all__ = ["loads", "dumps"]
