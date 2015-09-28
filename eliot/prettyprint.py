"""
API and command-line support for human-readable Eliot messages.
"""

from __future__ import unicode_literals

from datetime import datetime
from sys import stdin, stdout, argv
from ._bytesjson import loads

from six import text_type as unicode, PY2, PY3
if PY3:
    # Ensure binary stdin, since we expect specifically UTF-8 encoded
    # messages, not platform-encoding messages.
    stdin = stdin.buffer


def pretty_format(message):
    """
    Convert a message dictionary into a human-readable string.

    @param message: Message to parse, as dictionary.

    @return: Unicode string.
    """
    skip = {"timestamp", "task_uuid", "task_level", "action_counter",
            "message_type", "action_type", "action_status"}

    def add_field(previous, key, value):
        value = unicode(value).rstrip("\n")
        # Reindent second line and later to match up with first line's
        # indentation:
        lines = value.split("\n")
        indent = " " * (2 + len(key) + 2)  # lines are "  <key>: <value>"
        value = "\n".join([lines[0]] + [indent + l for l in lines[1:]])
        return "  %s: %s\n" % (key, value)

    remaining = ""
    for field in ["action_type", "message_type", "action_status"]:
        if field in message:
            remaining += add_field(remaining, field, message[field])
    for (key, value) in sorted(message.items()):
        if key not in skip:
            remaining += add_field(remaining, key, value)

    level = "/" + "/".join(map(unicode, message["task_level"]))
    return "%s@%s\n%sZ\n%s" % (
        message["task_uuid"],
        level,
        # If we were returning or storing the datetime we'd want to use an
        # explicit timezone instead of a naive datetime, but since we're
        # just using it for formatting we needn't bother.
        datetime.utcfromtimestamp(message["timestamp"]).isoformat(
            sep=str(" ")),
        remaining,
    )


_CLI_HELP = """\
Usage: cat messages | eliot-prettyprint

Convert Eliot messages into more readable format.

Reads JSON lines from stdin, write out pretty-printed results on stdout.
"""


def _main():
    """
    Command-line program that reads in JSON from stdin and writes out
    pretty-printed messages to stdout.
    """
    if argv[1:]:
        stdout.write(_CLI_HELP)
        raise SystemExit()
    for line in stdin:
        message = loads(line)
        result = pretty_format(message) + "\n"
        if PY2:
            result = result.encode("utf-8")
        stdout.write(result)


__all__ = ["pretty_format"]
