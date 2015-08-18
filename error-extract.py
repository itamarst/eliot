from __future__ import unicode_literals

import json
import sys
from datetime import datetime


def pretty_print(message):
    """
    Print human-readable messages to stdout.
    """
    skip = {"timestamp", "task_uuid", "task_level", "action_counter",
            "message_type", "action_type", "action_status"}

    def add_field(previous, key, value):
        return "  %s: %s\n" % (key, str(value).strip("\n"))

    remaining = ""
    for field in ["action_type", "message_type", "action_status"]:
        if field in message:
            remaining += add_field(remaining, field, message[field])
    for (key, value) in message.items():
        if key not in skip:
            remaining += add_field(remaining, key, value)

    level = "/" + "/".join(map(str, message["task_level"]))
    output = "%s%s %sZ\n%s\n" % (
        message["task_uuid"],
        level,
        datetime.utcfromtimestamp(message["timestamp"]).time().isoformat(),
        remaining,
    )
    if not sys.stdout.isatty():
        output = output.encode("utf-8")
    sys.stdout.write(output)


def main():
    for line in sys.stdin:
        try:
            message = json.loads(line)
        except ValueError:
            # Stupid systemd/journald corrupted the log message
            continue
        if (message.get("message_type") == "eliot:traceback" or
            (message.get("action_type") and
             message["action_status"] == "failed")):
            pretty_print(message)


main()

