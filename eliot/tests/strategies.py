"""
Hypothesis strategies for eliot.
"""

from __future__ import unicode_literals

from functools import partial
from six import text_type as unicode

from hypothesis.strategies import (
    builds,
    dictionaries,
    fixed_dictionaries,
    floats,
    integers,
    lists,
    just,
    none,
    one_of,
    recursive,
    text,
    uuids,
)

from pyrsistent import pmap, pvector, ny, thaw


from .._action import (
    ACTION_STATUS_FIELD, ACTION_TYPE_FIELD, FAILED_STATUS, STARTED_STATUS,
    SUCCEEDED_STATUS, TaskLevel, WrittenAction)
from .._message import (
    EXCEPTION_FIELD, REASON_FIELD, TASK_LEVEL_FIELD, TASK_UUID_FIELD,
    WrittenMessage)


task_level_indexes = integers(min_value=1, max_value=10)
# Task levels can be arbitrarily deep, but in the wild rarely as much as 100.
# Five seems a sensible average.
task_level_lists = lists(task_level_indexes, min_size=1, max_size=6)
task_levels = task_level_lists.map(lambda level: TaskLevel(level=level))


# Text generation is slow, and most of the things are short labels. We set
# a restricted alphabet so they're easier to read, and in general large
# amount of randomness in label generation doesn't enhance our testing in
# any way, since we don't parse type names or user field values.
labels = text(min_size=1, max_size=8, alphabet="CGAT")

timestamps = floats(min_value=0, max_value=1000.0)

message_core_dicts = fixed_dictionaries(
    dict(task_level=task_level_lists.map(pvector),
         task_uuid=uuids().map(unicode),
         timestamp=timestamps)).map(pmap)


# Text generation is slow. We can make it faster by not generating so
# much. These are reasonable values.
message_data_dicts = dictionaries(
    keys=labels, values=labels,
    # People don't normally put much more than ten fields in their
    # messages, surely?
    max_size=10,
).map(pmap)


def written_from_pmap(d):
    """
    Convert a C{pmap} to a C{WrittenMessage}.
    """
    return WrittenMessage.from_dict(thaw(d))


def union(*dicts):
    result = pmap().evolver()
    for d in dicts:
        # Work around bug in pyrsistent where it sometimes loses updates if
        # they contain some kv pairs that are identical to the ones in the
        # dict being updated.
        #
        # https://github.com/tobgu/pyrsistent/pull/54
        for key, value in d.items():
            if key in result and result[key] is value:
                continue
            result[key] = value
    return result.persistent()


message_dicts = builds(union, message_data_dicts, message_core_dicts)
written_messages = message_dicts.map(written_from_pmap)

_start_action_fields = fixed_dictionaries(
    { ACTION_STATUS_FIELD: just(STARTED_STATUS),
      ACTION_TYPE_FIELD: labels,
    })
start_action_message_dicts = builds(
    union, message_dicts, _start_action_fields).map(
        lambda x: x.update({TASK_LEVEL_FIELD: x[TASK_LEVEL_FIELD].set(-1, 1)}))
start_action_messages = start_action_message_dicts.map(
    written_from_pmap)


def sibling_task_level(message, n):
    return message.task_level.parent().level.append(n)


_end_action_fields = one_of(
    just({ACTION_STATUS_FIELD: SUCCEEDED_STATUS}),
    fixed_dictionaries({
        ACTION_STATUS_FIELD: just(FAILED_STATUS),
        # Text generation is slow. We can make it faster by not generating so
        # much. Thqese are reasonable values.
        EXCEPTION_FIELD: labels,
        REASON_FIELD: labels,
    }),
)


def _make_written_action(start_message, child_messages, end_message_dict):
    """
    Helper for creating arbitrary L{WrittenAction}s.

    The child messages and end message (if provided) will be updated to have
    the same C{task_uuid} as C{start_message}. Likewise, their C{task_level}s
    will be such that they follow on from C{start_message}.

    @param WrittenMessage start_message: The message to start the action with.
    @param child_messages: A sequence of L{WrittenAction}s and
        L{WrittenMessage}s that make up the action.
    @param (PMap | None) end_message_dict: A dictionary that makes up an end
        message. If None, then the action is unfinished.

    @return: A L{WrittenAction}
    """
    task_uuid = start_message.task_uuid
    children = []

    for i, child in enumerate(child_messages, 2):
        task_level = TaskLevel(level=sibling_task_level(start_message, i))
        children.append(reparent_action(task_uuid, task_level, child))

    if end_message_dict:
        end_message = written_from_pmap(
            union(end_message_dict, {
                ACTION_TYPE_FIELD: start_message.contents[ACTION_TYPE_FIELD],
                TASK_UUID_FIELD: task_uuid,
                TASK_LEVEL_FIELD: sibling_task_level(
                    start_message, 2 + len(children)),
            })
        )
    else:
        end_message = None

    return WrittenAction.from_messages(start_message, children, end_message)


written_actions = recursive(
    written_messages,
    lambda children: builds(
        _make_written_action,
        start_message=start_action_messages,
        child_messages=lists(children, max_size=5),
        end_message_dict=builds(
            union, message_dicts, _end_action_fields) | none(),
    ),
)


def _map_messages(f, written_action):
    """
    Map C{f} across all of the messages that make up C{written_action}.

    This is a structure-preserving map operation. C{f} will be applied to all
    messages that make up C{written_action}: the start message, end message,
    and children. If any of the children are themselves L{WrittenAction}s, we
    recurse down into them.

    @param f: A function that takes a L{WrittenMessage} and returns a new
        L{WrittenMessage}.
    @param (WrittenAction | WrittenMessage) written_action: A written

    @return: A L{WrittenMessage} if C{written_action} is a C{WrittenMessage},
        a L{WrittenAction} otherwise.
    """
    if isinstance(written_action, WrittenMessage):
        return f(written_action)

    start_message = f(written_action.start_message)
    children = written_action.children.transform([ny], partial(_map_messages, f))
    if written_action.end_message:
        end_message = f(written_action.end_message)
    else:
        end_message = None

    return WrittenAction.from_messages(
        start_message=start_message,
        children=pvector(children),
        end_message=end_message,
    )


def reparent_action(task_uuid, task_level, written_action):
    """
    Return a version of C{written_action} that has the given C{task_uuid} and
    is rooted at the given C{task_level}.

    @param UUID task_uuid: The new task UUID.
    @param TaskLevel task_level: The new task level.
    @param (WrittenAction | WrittenMessage) written_action: The action or
        message to update.

    @return: A new version of C{written_action}.
    """
    new_prefix = list(task_level.level)
    old_prefix_len = len(written_action.task_level.level)

    def fix_message(message):
        return (
            message.transform(
                ['_logged_dict', TASK_LEVEL_FIELD],
                lambda level: new_prefix + level[old_prefix_len:])
            .transform(['_logged_dict', TASK_UUID_FIELD], task_uuid))

    return _map_messages(fix_message, written_action)
