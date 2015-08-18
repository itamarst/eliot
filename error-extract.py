from __future__ import unicode_literals

import json
import sys
from datetime import datetime


def pretty_print(message, separator=True):
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
    output = "%s%s %sZ\n%s" % (
        message["task_uuid"],
        level,
        datetime.utcfromtimestamp(message["timestamp"]).time().isoformat(),
        remaining,
    )
    if separator:
        output += "\n"
    sys.stdout.write(output)


def main():
    cached_start_messages = {}

    for line in sys.stdin:
        try:
            message = json.loads(line)
        except ValueError:
            # Stupid systemd/journald corrupted the log message
            continue
        if message.get("message_type") == "eliot:traceback":
            pretty_print(message)
        elif message.get("action_type"):
            action_type = message["action_type"]
            task_uuid = message["task_uuid"]
            task_level = tuple(message["task_level"][:-1])
            status = message["action_status"]
            key = (action_type, task_uuid, task_level)
            if status == "started":
                cached_start_messages[key] = message
            else:
                try:
                    start_message = cached_start_messages.pop(key)
                except KeyError:
                    start_message = None
                if status == "failed":
                    if start_message:
                        pretty_print(start_message, separator=False)
                    pretty_print(message)


main()

