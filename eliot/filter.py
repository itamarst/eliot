"""
Command line program for filtering line-based Eliot logs.
"""

from __future__ import unicode_literals, absolute_import

if __name__ == '__main__':
    import eliot.filter
    eliot.filter.main()

import sys
from datetime import datetime, timedelta

from . import _bytesjson as json


class _JSONEncoder(json.JSONEncoder):
    """
    JSON encoder that supports L{datetime}.
    """

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)


_encoder = _JSONEncoder()


class EliotFilter(object):
    """
    Filter Eliot log lines using a Python expression.

    @ivar code: A Python code object, the compiled filter expression.
    """
    _SKIP = object()

    def __init__(self, expr, incoming, output):
        """
        @param expr: A Python expression that will be called for each log message.
        @type expr: L{str}

        @param incoming: An iterable of L{bytes}, each of which is a serialized
            Eliot message.

        @param output: A file to which output should be written.
        @type output: L{file} or a file-like object.
        """
        self.code = compile(expr, "<string>", "eval")
        self.incoming = incoming
        self.output = output

    def run(self):
        """
        For each incoming message, decode the JSON, evaluate expression, encode
        as JSON and write that to the output file.
        """
        for line in self.incoming:
            message = json.loads(line)
            result = self._evaluate(message)
            if result is self._SKIP:
                continue
            self.output.write(_encoder.encode(result).encode("utf-8") + b"\n")

    def _evaluate(self, message):
        """
        Evaluate the expression with the given Python object in its locals.

        @param message: A decoded JSON input.

        @return: The resulting object.
        """
        return eval(
            self.code,
            globals(), {
                "J": message,
                "timedelta": timedelta,
                "datetime": datetime,
                "SKIP": self._SKIP})


USAGE = b"""\
Usage: cat eliot.log | python -m eliot.filter <expr>

Read JSON-expression per line from stdin, and filter it using a Python
expression <expr>.

The expression will have a local `J` containing decoded JSON. `datetime` and
`timedelta` from Python's `datetime` module are also available as locals,
containing the corresponding classes. `SKIP` is also available, if it's the
expression result that indicates nothing should be output.

The output will be written to stdout using JSON serialization. `datetime`
objects will be serialized to ISO format.

Examples:

- Pass through the messages unchanged:

    $ cat eliot.log | python -m eliot.filter J

- Retrieve a specific field from a specific message type, dropping messages
  of other types:

    $ cat eliot.log | python -m eliot.filter \\
        "J['field'] if J.get('message_type') == 'my:message' else SKIP"
"""


def main(sys=sys):
    """
    Run the program.

    Accept arguments from L{sys.argv}, read from L{sys.stdin}, write to
    L{sys.stdout}.

    @param sys: An object with same interface and defaulting to the L{sys}
        module.
    """
    if len(sys.argv) != 2:
        sys.stderr.write(USAGE)
        return 1
    EliotFilter(sys.argv[1], sys.stdin, sys.stdout).run()
    return 0
