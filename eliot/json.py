"""Custom JSON encoding support."""

from typing import Callable
import json
import sys


class EliotJSONEncoder(json.JSONEncoder):
    """
    DEPRECATED. JSON encoder with additional functionality.

    In particular, supports NumPy types.
    """

    def default(self, o):
        return json_default(o)


def json_default(o: object) -> object:
    """
    JSON object encoder for non-standard types.  In particular, supports NumPy
    types.  If you are wrappnig it, call it last, as it will raise a
    ``TypeError`` on unsupported types.
    """
    numpy = sys.modules.get("numpy", None)
    if numpy is not None:
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
    raise TypeError("Unsupported type")


def _encoder_to_default_function(
    encoder: json.JSONEncoder,
) -> Callable[[object], object]:
    """
    Convert an encoder into a default function usable by ``orjson``.
    """

    def default(o: object) -> object:
        return encoder.default(o)

    return default


try:
    from orjson import dumps as _dumps_bytes

    def _dumps_unicode(o: object, default=None) -> str:
        return _dumps_bytes(o, default=default).decode("utf-8")

except ImportError:

    def _dumps_bytes(o: object, default=None) -> bytes:
        """Serialize an object to JSON, output bytes."""
        return json.dumps(o, default=default).encode("utf-8")

    _dumps_unicode = json.dumps

__all__ = ["EliotJSONEncoder", "json_default"]
