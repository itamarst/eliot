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
        pandas = sys.modules.get("pandas", None)
        if numpy is not None or pandas is not None:
            if isinstance(o, numpy.floating):
                return float(o)
            if isinstance(o, numpy.integer):
                return int(o)
            if isinstance(o, numpy.bool_):
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
            if isinstance(obj, pandas.DataFrame):
                shape = {"rows": obj.shape[0], "columns": obj.shape[1]}
                dtypesDict = obj.dtypes.to_dict()
                # Convert dtypes to strings for serialization
                for key, val in dtypesDict.items():
                    dtypesDict[key] = str(val)
                # For large dataframes take a sample
                if obj.memory_usage(deep=True).sum() / 1e6 > 1:
                    obj = obj.sample(numpy.min([100, len(obj)]))
                return {
                    "shape": shape,
                    "columns": dtypesDict,
                    "data": obj.to_json(),
                }
        return json.JSONEncoder.default(self, o)


__all__ = ["EliotJSONEncoder"]
