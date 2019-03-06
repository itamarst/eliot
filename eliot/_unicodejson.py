"""Dump JSON to unicode strings."""

from functools import partial
from json import dumps, JSONEncoder

try:
    import rapidjson

    # Redefine using rapidjson:
    def dumps(obj, cls=JSONEncoder):
        return rapidjson.dumps(obj, default=cls().default)

except ImportError:
    pass
