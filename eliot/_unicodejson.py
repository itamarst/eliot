"""Dump JSON to unicode strings."""

from functools import partial
from json import dumps, JSONEncoder

try:
    import orjson

    # Redefine using orjson:
    def dumps(obj, cls=JSONEncoder):
        return str(
            orjson.dumps(obj, default=partial(cls.default, cls())),
            "utf-8"
        )
except ImportError:
    pass
