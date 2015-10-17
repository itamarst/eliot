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


class ActionStructure(PClass):
    type = field(type=unicode, mandatory=True)
    children = pvector_field(object)  # XXX ("StubAction", unicode))

    @classmethod
    def from_tree(cls, tree_or_message):
        if isinstance(tree_or_message, list):
            return cls(
                type=TYPES.example(),
                children=[cls.from_tree(o) for o in tree_or_message])
        else:
            return tree_or_message

    @classmethod
    def from_written(cls, written):
        if isinstance(written, WrittenMessage):
            return written.as_dict()[MESSAGE_TYPE_FIELD]
        else:  # WrittenAction
            if not written.end_message:# or written.end_message.as_dict()[MESSAGE_TYPE_FIELD]:
                raise AssertionError("XXX ugh this is a bad check")
            return cls(
                type=written.action_type,
                children=[cls.from_written(o) for o in written.children])

    @classmethod
    def to_eliot(cls, structure_or_message, logger):
        if isinstance(structure_or_message, cls):
            action = structure_or_message
            with start_action(logger, action_type=action.type):
                for child in action.children:
                    cls.to_eliot(child, logger)
        else:
            Message.new(message_type=structure_or_message).write(logger)
        return logger.messages


def _build_structure_strategy():
    strategy = st.recursive(TYPES, st.lists, max_leaves=10)
    strategy = strategy.map(ActionStructure.from_tree)

    def structure_and_messages(structure):
        messages = ActionStructure.to_eliot(structure, MemoryLogger())
        return st.permutations(messages).map(
            lambda permuted: (structure, permuted))
    strategy = strategy.flatmap(structure_and_messages)
    return strategy


TYPES = st.text(min_size=1, average_size=3, alphabet=u"CGAT")
ACTION_STRUCTURES = _build_structure_strategy()


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
    @given(structure_and_messages=ACTION_STRUCTURES)
    def test_parse_from_random_order(self, structure_and_messages):
        action_structure, messages = structure_and_messages

        task = Task.create(messages[0])
        for message in messages[1:]:
            task = task.add(message)

        # Assert parsed structure matches input structure:
        parsed_structure = ActionStructure.from_written(task.root())
        self.assertEqual(parsed_structure, action_structure)
