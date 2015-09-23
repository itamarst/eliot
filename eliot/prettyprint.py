"""
API and command-line support for human-readable Eliot messages.
"""

from __future__ import unicode_literals

from datetime import datetime
from sys import stdin, stdout
from json import loads

from six import text_type as unicode


def pretty_print(message):
    """
    Convert a message dictionary into a human-readable string.

    @param message: Message to parse, as dictionary.

    @return: Unicode string.
    """
    skip = {"timestamp", "task_uuid", "task_level", "action_counter",
            "message_type", "action_type", "action_status"}

    def add_field(previous, key, value):
        return "  %s: %s\n" % (key, str(value).strip("\n"))

    remaining = ""
    for field in ["action_type", "message_type", "action_status"]:
        if field in message:
            remaining += add_field(remaining, field, message[field])
    for (key, value) in sorted(message.items()):
        if key not in skip:
            remaining += add_field(remaining, key, value)

    level = "/" + "/".join(map(unicode, message["task_level"]))
    return "%s%s\n%sZ\n%s\n" % (
        message["task_uuid"],
        level,
        datetime.utcfromtimestamp(message["timestamp"]).isoformat(),
        remaining,
    )


def _main():
    """
    Command-line program that reads in JSON from stdin and writes out
    pretty-printed messages to stdout.
    """
    for line in stdin:
        message = loads(line)
        result = pretty_print(message)
        stdout.write(result.encode("utf-8"))
