"""
API and command-line support for human-readable Eliot messages.
"""

import pprint
import argparse
from datetime import datetime
from sys import stdin, stdout
from collections import OrderedDict
from json import dumps

from ._bytesjson import loads
from ._message import (
    TIMESTAMP_FIELD,
    TASK_UUID_FIELD,
    TASK_LEVEL_FIELD,
    MESSAGE_TYPE_FIELD,
)
from ._action import ACTION_TYPE_FIELD, ACTION_STATUS_FIELD


# Ensure binary stdin, since we expect specifically UTF-8 encoded
# messages, not platform-encoding messages.
stdin = stdin.buffer


# Fields that all Eliot messages are expected to have:
REQUIRED_FIELDS = {TASK_LEVEL_FIELD, TASK_UUID_FIELD, TIMESTAMP_FIELD}

# Fields that get treated specially when formatting.
_skip_fields = {
    TIMESTAMP_FIELD,
    TASK_UUID_FIELD,
    TASK_LEVEL_FIELD,
    MESSAGE_TYPE_FIELD,
    ACTION_TYPE_FIELD,
    ACTION_STATUS_FIELD,
}

# First fields to render:
_first_fields = [ACTION_TYPE_FIELD, MESSAGE_TYPE_FIELD, ACTION_STATUS_FIELD]


def _render_timestamp(message: dict) -> str:
    """Convert a message's timestamp to a string."""
    # If we were returning or storing the datetime we'd want to use an
    # explicit timezone instead of a naive datetime, but since we're
    # just using it for formatting we needn't bother.
    return datetime.utcfromtimestamp(message[TIMESTAMP_FIELD]).isoformat(sep="T")


def pretty_format(message):
    """
    Convert a message dictionary into a human-readable string.

    @param message: Message to parse, as dictionary.

    @return: Unicode string.
    """

    def add_field(previous, key, value):
        value = (
            pprint.pformat(value, width=40).replace("\\n", "\n ").replace("\\t", "\t")
        )
        # Reindent second line and later to match up with first line's
        # indentation:
        lines = value.split("\n")
        # indent lines are "  <key length>|  <value>"
        indent = "{}| ".format(" " * (2 + len(key)))
        value = "\n".join([lines[0]] + [indent + l for l in lines[1:]])
        return "  %s: %s\n" % (key, value)

    remaining = ""
    for field in _first_fields:
        if field in message:
            remaining += add_field(remaining, field, message[field])
    for (key, value) in sorted(message.items()):
        if key not in _skip_fields:
            remaining += add_field(remaining, key, value)

    level = "/" + "/".join(map(str, message[TASK_LEVEL_FIELD]))
    return "%s -> %s\n%sZ\n%s" % (
        message[TASK_UUID_FIELD],
        level,
        _render_timestamp(message),
        remaining,
    )


def compact_format(message: dict) -> str:
    """Format an Eliot message into a single line.

    The message is presumed to be JSON-serializable.
    """
    ordered_message = OrderedDict()
    for field in _first_fields:
        if field in message:
            ordered_message[field] = message[field]
    for (key, value) in sorted(message.items()):
        if key not in _skip_fields:
            ordered_message[key] = value
    # drop { and } from JSON:
    rendered = " ".join(
        "{}={}".format(key, dumps(value, separators=(",", ":")))
        for (key, value) in ordered_message.items()
    )

    return "%s%s %sZ %s" % (
        message[TASK_UUID_FIELD],
        "/" + "/".join(map(str, message[TASK_LEVEL_FIELD])),
        _render_timestamp(message),
        rendered,
    )


_CLI_HELP = """\
Convert Eliot messages into more readable format.

Reads JSON lines from stdin, write out pretty-printed results on stdout.
"""


def _main():
    """
    Command-line program that reads in JSON from stdin and writes out
    pretty-printed messages to stdout.
    """
    parser = argparse.ArgumentParser(
        description=_CLI_HELP, usage="cat messages | %(prog)s [options]"
    )
    parser.add_argument(
        "-c",
        "--compact",
        action="store_true",
        dest="compact",
        help="Compact format, one message per line.",
    )
    args = parser.parse_args()
    if args.compact:
        formatter = compact_format
    else:
        formatter = pretty_format

    for line in stdin:
        try:
            message = loads(line)
        except ValueError:
            stdout.write("Not JSON: {}\n\n".format(line.rstrip(b"\n")))
            continue
        if REQUIRED_FIELDS - set(message.keys()):
            stdout.write("Not an Eliot message: {}\n\n".format(line.rstrip(b"\n")))
            continue
        result = formatter(message) + "\n"
        stdout.write(result)


__all__ = ["pretty_format", "compact_format"]
