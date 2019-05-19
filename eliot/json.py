"""Custom JSON encoding support."""

from __future__ import absolute_import

import json
import sys


class EliotJSONEncoder(json.JSONEncoder):
    """JSON encoder with additional functionality.

    In particular, supports NumPy types.
    """

    def default(self, o):
        numpy = sys.modules.get("numpy", None)
        if numpy is not None:
            if isinstance(o, numpy.floating):
                return float(o)
            if isinstance(o, numpy.integer):
                return int(o)
            if isinstance(o, (numpy.bool, numpy.bool_)):
                return bool(o)
            if isinstance(o, numpy.ndarray):
                if o.size > 10000:
                    # Too big to want to log as-is, log a summary:
                    return {
                        "array_start": o.flat[:10000].tolist(),
                        "original_shape": o.shape,
                    }
                else:
                    return o.tolist()
        return json.JSONEncoder.default(self, o)


__all__ = ["EliotJSONEncoder"]
