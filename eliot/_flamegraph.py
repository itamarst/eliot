"""
XXX the above is all wrong since it is not cumulative, and doesn't deal with fact that Eliot logs aren't quite the same as callstacks since child actions may complete after parent actions.

We want instead a tree datastructure, I think, where each action refers to its children. The recorded elapsed time for an action is the actual elapsed time (end message timestamp - start message timestamp) minus the actual time elapsed by its direct children that *overlaps*. Non-overlapping bits shouldn't be subtracted.

If an action overlaps only partially with its parent it should end up with two entries: one for the overlap with that stack and one for non-overlap without ancestors in its stack.

Same datastructure should be able to cover kcachegrind format as well.
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
