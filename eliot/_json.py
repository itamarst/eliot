"""Custom JSON encoding support."""

import json

import numpy


class EliotJSONEncoder(json.JSONEncoder):
    """JSON encoder with additional functionality.

    In particular, supports NumPy types.
    """

    def default(self, o):
        if isinstance(o, numpy.floating):
            return float(o)
        if isinstance(o, numpy.integer):
            return int(o)
        if isinstance(o, (numpy.bool, numpy.bool_)):
            return bool(o)
        if isinstance(o, numpy.ndarray):
            return o.tolist()
        return json.JSONEncoder.default(self, o)

__all__ = ["EliotJSONEncoder"]

