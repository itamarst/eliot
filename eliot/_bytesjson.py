"""
Python 2/3 JSON encoding/decoding, emulating Python 2's json module.

Python 3 json module doesn't support decoding bytes or encoding. Rather than
adding isinstance checks in main code path which would slow down Python 2,
instead we write our encoder that can support those.
"""

from __future__ import absolute_import

from functools import partial
import json as pyjson
import warnings

from six import PY2

def _py3_dumps(obj, cls=pyjson.JSONEncoder):
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
                    " on Python 3", DeprecationWarning
                )
                return o.decode("utf-8")
            return cls.default(self, o)

    return _standard_dumps(obj, cls=WithBytes)


if PY2:
    # No need for the above on Python 2
    loads, dumps = pyjson.loads, pyjson.dumps
else:
    try:
        from rapidjson import loads, dumps
    except ImportError:
        loads, dumps = pyjson.loads, _py3_dumps

__all__ = ["loads", "dumps"]
