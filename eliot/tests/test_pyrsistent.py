from uuid import UUID

import testtools

from hypothesis import given
from hypothesis.strategies import (
    basic,
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
)

from pyrsistent import pmap, pvector


from .._action import (
    ACTION_STATUS_FIELD, ACTION_TYPE_FIELD, FAILED_STATUS, STARTED_STATUS,
    SUCCEEDED_STATUS, WrittenAction)
from .._message import (
    EXCEPTION_FIELD, REASON_FIELD, TASK_LEVEL_FIELD, TASK_UUID_FIELD,
    WrittenMessage)


TASK_LEVEL_INDEXES = integers(min_value=1)
TASK_LEVEL_LISTS = lists(TASK_LEVEL_INDEXES, min_size=1, average_size=5)

# Text generation is slow, and most of the things are short labels.
LABELS = text(average_size=5)

TIMESTAMPS = floats(min_value=0)

UUIDS = basic(generate=lambda r, _: UUID(int=r.getrandbits(128)))

MESSAGE_CORE_DICTS = fixed_dictionaries(
    dict(task_level=TASK_LEVEL_LISTS.map(pvector),
         task_uuid=UUIDS,
         timestamp=TIMESTAMPS)).map(pmap)


# Text generation is slow. We can make it faster by not generating so
# much. These are reasonable values.
MESSAGE_DATA_DICTS = dictionaries(
    keys=LABELS, values=text(average_size=10),
    # People don't normally put much more than twenty fields in their
    # messages, surely?
    average_size=10,
).map(pmap)


def union(*dicts):
    result = pmap()
    for d in dicts:
        result = result.update(d)
    return result


MESSAGE_DICTS = builds(union, MESSAGE_DATA_DICTS, MESSAGE_CORE_DICTS)
WRITTEN_MESSAGES = MESSAGE_DICTS.map(WrittenMessage.from_dict)

_start_action_fields = fixed_dictionaries(
    { ACTION_STATUS_FIELD: just(STARTED_STATUS),
      ACTION_TYPE_FIELD: LABELS,
    })
START_ACTION_MESSAGE_DICTS = builds(
    union, MESSAGE_DICTS, _start_action_fields).map(
        lambda x: x.update({TASK_LEVEL_FIELD: x[TASK_LEVEL_FIELD].set(-1, 1)}))
START_ACTION_MESSAGES = START_ACTION_MESSAGE_DICTS.map(WrittenMessage.from_dict)


def sibling_task_level(message, n):
    return message.task_level.parent().level.append(n)


def child_task_level(task_level, i):
    return task_level.transform(['level'], lambda level: level.append(i))


_end_action_fields = one_of(
    just({ACTION_STATUS_FIELD: SUCCEEDED_STATUS}),
    fixed_dictionaries({
        ACTION_STATUS_FIELD: just(FAILED_STATUS),
        # Text generation is slow. We can make it faster by not generating so
        # much. These are reasonable values.
        EXCEPTION_FIELD: text(average_size=20),
        REASON_FIELD: text(average_size=20),
    }),
)


def _pyr_make_written_action(start_message, child_messages, end_message_dict):
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

    if end_message_dict:
        new_fields = {
            ACTION_TYPE_FIELD: start_message.contents[ACTION_TYPE_FIELD],
            TASK_UUID_FIELD: task_uuid,
            TASK_LEVEL_FIELD: sibling_task_level(
                start_message, 2),
        }
        new_dict = end_message_dict.update(new_fields)
        # XXX: This is the weird behaviour.
        assert ACTION_TYPE_FIELD in new_dict
        end_message = WrittenMessage.from_dict(new_dict)
    else:
        end_message = None

    return WrittenAction.from_messages(start_message, [], end_message)


PYR_WRITTEN_ACTIONS = recursive(
    WRITTEN_MESSAGES,
    lambda children: builds(
        _pyr_make_written_action,
        start_message=START_ACTION_MESSAGES,
        # XXX: If I restrict the list size to 1 (or just pass empty list), the
        # test always passes.
        child_messages=lists(children, average_size=5),
        # XXX: If I drop the '| none()', the test always passes.
        end_message_dict=builds(union, MESSAGE_DICTS, _end_action_fields) | none(),
    ),
)


class PyrsistentTests(testtools.TestCase):

    @given(PYR_WRITTEN_ACTIONS)
    def test_trivial(self, _ignored):
        pass
