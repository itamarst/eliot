"""
Tests for L{eliot._parse}.
"""

from unittest import TestCase

from hypothesis import strategies as st, given

from pyrsistent import PClass, field, pvector_field

from .. import start_action, Message
from ..testing import MemoryLogger
from .._parse import Task
from .._message import WrittenMessage, MESSAGE_TYPE_FIELD
from .._action import FAILED_STATUS, ACTION_TYPE_FIELD


class ActionStructure(PClass):
    type = field(type=unicode)
    children = pvector_field(object)  # XXX ("StubAction", unicode))
    failed = field(type=bool)

    @classmethod
    def from_written(cls, written):
        if isinstance(written, WrittenMessage):
            return written.as_dict()[MESSAGE_TYPE_FIELD]
        else:  # WrittenAction
            if not written.end_message or (
                    written.end_message.as_dict()[ACTION_TYPE_FIELD] !=
                    written.action_type):
                raise AssertionError("Wrong type on end message.")
            return cls(
                type=written.action_type,
                failed=(written.status == FAILED_STATUS),
                children=[cls.from_written(o) for o in written.children])

    @classmethod
    def to_eliot(cls, structure_or_message, logger):
        if isinstance(structure_or_message, cls):
            action = structure_or_message
            try:
                with start_action(logger, action_type=action.type):
                    for child in action.children:
                        cls.to_eliot(child, logger)
                    if structure_or_message.failed:
                        raise RuntimeError("Make the eliot action fail.")
            except RuntimeError:
                pass
        else:
            Message.new(message_type=structure_or_message).write(logger)
        return logger.messages


TYPES = st.text(min_size=1, average_size=3, alphabet=u"CGAT")


@st.composite
def action_structures(draw):
    tree = draw(st.recursive(TYPES, st.lists, max_leaves=10))

    def to_structure(tree_or_message):
        if isinstance(tree_or_message, list):
            return ActionStructure(
                type=draw(TYPES),
                failed=draw(st.booleans()),
                children=[to_structure(o) for o in tree_or_message])
        else:
            return tree_or_message
    return to_structure(tree)


def _structure_and_messages(structure):
    messages = ActionStructure.to_eliot(structure, MemoryLogger())
    return st.permutations(messages).map(
        lambda permuted: (structure, permuted))
STRUCTURES_WITH_MESSAGES = action_structures().flatmap(_structure_and_messages)


class TaskTests(TestCase):
    """
    Tests for L{Task}.

    Create a tree of Eliot actions and messages using Hypothesis. Feed
    resulting messages into tree parser in random order. At the end we should
    get expected result. The key idea here is that if any random order is
    correct then the intermediate states must be correct too.

    Additional coverage is then needed that is specific to the intermediate
    states, i.e. missing messages.
    """
    @given(structure_and_messages=STRUCTURES_WITH_MESSAGES)
    def test_parse_from_random_order(self, structure_and_messages):
        action_structure, messages = structure_and_messages

        task = Task()
        for message in messages:
            task = task.add(message)

        # Assert parsed structure matches input structure:
        parsed_structure = ActionStructure.from_written(task.root())
        self.assertEqual(parsed_structure, action_structure)
