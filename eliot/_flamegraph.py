"""
Eliot actions are not quite the same as a callstack since a child can
live on after a parent.

Imagine the following tree:

|-----[root]-----|
   |-[child]-|
      |--[grandchild]--|

A sampling of running actions would likely find:

rrr           rrrr
   ccc
      gggggggggggggggggg

The fact that grandchild overlaps with root in the end after child has
ended means they're likely both running at same time. Thus a sampling
strategy would have found both. Otherwise it's not clear how the root
could ever end.

We can use the following algorithm to implement this:
Record each action's callstack (its type and ancestor actions' types) for
the time span from start to end where it has no child actions
running. Descendants don't count, only children.  This can easily be
calculated by constructing a tree of actions and traversing it from the
root.

This is not a guarantee that is what is going on exactly but it's likely
a reasonable approximation, and will be accurate for blocking code.
"""
from sys import stdin, stdout

from pyrsistent import PRecord, pmap_field, field, discard

from ._message import (
    TIMESTAMP_FIELD, TASK_UUID_FIELD, TASK_LEVEL_FIELD,
)
from ._action import (
    ACTION_TYPE_FIELD, ACTION_STATUS_FIELD, STARTED_STATUS, TaskLevel,
)
from ._bytesjson import loads


class CallStacks(PRecord):
    starts = pmap_field(tuple, tuple)
    last_timestamp = field(initial=0.0)

    def update_timestamp(self, message):
        timestamp = message[TIMESTAMP_FIELD]
        if timestamp > self.last_timestamp:
            return self.set(last_timestamp=timestamp)
        else:
            return self


def get_key(message):
    return (message[TASK_UUID_FIELD],
            TaskLevel(level=message[TASK_LEVEL_FIELD]).parent())


def _main():
    """
    Command-line program that reads in JSON from stdin and writes out
    pretty-printed messages to stdout.
    """
    calls = CallStacks()

    for line in stdin:
        message = loads(line)
        calls = calls.update_timestamp(message)
        if ACTION_TYPE_FIELD in message:
            if message[ACTION_STATUS_FIELD] == STARTED_STATUS:
                level = TaskLevel(level=message[TASK_LEVEL_FIELD])
                current_type = message[ACTION_TYPE_FIELD]
                if level.level == [1]:
                    type_stack = [current_type]
                else:
                    parent_level = level.parent().parent()
                    type_stack = calls.starts.get(
                        (message[TASK_UUID_FIELD], parent_level), [[]])[0] + [
                            current_type]
                calls = calls.transform(
                    ["starts", get_key(message)],
                    (type_stack, message[TIMESTAMP_FIELD]))
            else:
                key = get_key(message)
                type_stack, start_timestamp = calls.starts.get(
                    key, (None, None))
                if start_timestamp is not None:
                    calls = calls.transform(["starts", key], discard)
                    stdout.write(";".join(type_stack) + " %d\n" % (
                        (1000000 * message[TIMESTAMP_FIELD] -
                         1000000 * start_timestamp),))
