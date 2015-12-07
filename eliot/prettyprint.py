"""
API and command-line support for human-readable Eliot messages.
"""

from __future__ import unicode_literals

import pprint
from datetime import datetime
from sys import stdin, stdout, argv

from ._bytesjson import loads
from ._message import (
    TIMESTAMP_FIELD, TASK_UUID_FIELD, TASK_LEVEL_FIELD, MESSAGE_TYPE_FIELD,
)
from ._action import ACTION_TYPE_FIELD, ACTION_STATUS_FIELD
from ._util import load_module

from six import text_type as unicode, PY2, PY3
if PY3:
    # Ensure binary stdin, since we expect specifically UTF-8 encoded
    # messages, not platform-encoding messages.
    stdin = stdin.buffer


# On Python 2 pprint formats unicode with u'' prefix, which is inconsistent
# with Python 3 and not very nice to read. So we modify a copy to omit the u''.
if PY2:
    def _nicer_unicode_repr(o, original_repr=repr):
        if isinstance(o, unicode):
            return original_repr(o.encode("utf-8"))
        else:
            return original_repr(o)
    pprint = load_module(b"unicode_pprint", pprint)
    pprint.repr = _nicer_unicode_repr


# Fields that all Eliot messages are expected to have:
REQUIRED_FIELDS = {TASK_LEVEL_FIELD, TASK_UUID_FIELD, TIMESTAMP_FIELD}


def pretty_format(message):
    """
    Convert a message dictionary into a human-readable string.

    @param message: Message to parse, as dictionary.

    @return: Unicode string.
    """
    skip = {TIMESTAMP_FIELD, TASK_UUID_FIELD, TASK_LEVEL_FIELD,
            MESSAGE_TYPE_FIELD, ACTION_TYPE_FIELD, ACTION_STATUS_FIELD}

    def add_field(previous, key, value):
        value = unicode(pprint.pformat(value, width=40)).replace(
            "\\n", "\n ").replace("\\t", "\t")
        # Reindent second line and later to match up with first line's
        # indentation:
        lines = value.split("\n")
        # indent lines are "  <key length>|  <value>"
        indent = "{}| ".format(" " * (2 + len(key)))
        value = "\n".join([lines[0]] + [indent + l for l in lines[1:]])
        return "  %s: %s\n" % (key, value)

    remaining = ""
    for field in [ACTION_TYPE_FIELD, MESSAGE_TYPE_FIELD, ACTION_STATUS_FIELD]:
        if field in message:
            remaining += add_field(remaining, field, message[field])
    for (key, value) in sorted(message.items()):
        if key not in skip:
            remaining += add_field(remaining, key, value)

    level = "/" + "/".join(map(unicode, message[TASK_LEVEL_FIELD]))
    return "%s -> %s\n%sZ\n%s" % (
        message[TASK_UUID_FIELD],
        level,
        # If we were returning or storing the datetime we'd want to use an
        # explicit timezone instead of a naive datetime, but since we're
        # just using it for formatting we needn't bother.
        datetime.utcfromtimestamp(message[TIMESTAMP_FIELD]).isoformat(
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
        try:
            message = loads(line)
        except ValueError:
            stdout.write("Not JSON: {}\n\n".format(line.rstrip(b"\n")))
            continue
        if REQUIRED_FIELDS - set(message.keys()):
            stdout.write("Not an Eliot message: {}\n\n".format(
                line.rstrip(b"\n")))
            continue
        result = pretty_format(message) + "\n"
        if PY2:
            result = result.encode("utf-8")
        stdout.write(result)


__all__ = ["pretty_format"]
