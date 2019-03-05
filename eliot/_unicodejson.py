"""Dump JSON to unicode strings."""

from functools import partial
from json import dumps, JSONEncoder

try:
    from rapidjson import dumps
except ImportError:
    pass
