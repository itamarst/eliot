"""
Tests for L{eliot._parse}.
"""

from __future__ import unicode_literals

from unittest import TestCase
from itertools import chain, izip_longest

from six import text_type as unicode

from hypothesis import strategies as st, given, assume

from pyrsistent import PClass, field, pvector_field

from .. import start_action, Message
from ..testing import MemoryLogger
from .._parse import Task, Parser
from .._message import (
    WrittenMessage, MESSAGE_TYPE_FIELD, TASK_LEVEL_FIELD, TASK_UUID_FIELD,
)
from .._action import FAILED_STATUS, ACTION_STATUS_FIELD, WrittenAction
from .strategies import labels


class ActionStructure(PClass):
    """
    A tree structure used to generate/compare to Eliot trees.

    Individual messages are encoded as a unicode string; actions are
    encoded as a L{ActionStructure} instance.
    """
    type = field(type=(unicode, None.__class__))
    children = pvector_field(object)  # XXX ("StubAction", unicode))
    failed = field(type=bool)

    @classmethod
    def from_written(cls, written):
        """
        Create an L{ActionStructure} or L{unicode} from a L{WrittenAction} or
        L{WrittenMessage}.
        """
        if isinstance(written, WrittenMessage):
            return written.as_dict()[MESSAGE_TYPE_FIELD]
        else:  # WrittenAction
            if not written.end_message:
                raise AssertionError("Missing end message.")
            return cls(
                type=written.action_type,
                failed=(written.end_message.contents[ACTION_STATUS_FIELD] ==
                        FAILED_STATUS),
                children=[cls.from_written(o) for o in written.children])

    @classmethod
    def to_eliot(cls, structure_or_message, logger):
        """
        Given a L{ActionStructure} or L{unicode}, generate appropriate
        structured Eliot log mesages to given L{MemoryLogger}.
        """
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


@st.composite
def action_structures(draw):
    """
    A Hypothesis strategy that creates a tree of L{ActionStructure} and
    L{unicode}.
    """
    tree = draw(st.recursive(labels, st.lists, max_leaves=50))

    def to_structure(tree_or_message):
        if isinstance(tree_or_message, list):
            return ActionStructure(
                type=draw(labels),
                failed=draw(st.booleans()),
                children=[to_structure(o) for o in tree_or_message])
        else:
            return tree_or_message
    return to_structure(tree)


def _structure_and_messages(structure):
    messages = ActionStructure.to_eliot(structure, MemoryLogger())
    return st.permutations(messages).map(
        lambda permuted: (structure, permuted))
# Hypothesis strategy that creates a tuple of ActionStructure/unicode and
# corresponding serialized Eliot messages, randomly shuffled.
STRUCTURES_WITH_MESSAGES = action_structures().flatmap(_structure_and_messages)


class TaskTests(TestCase):
    """
    Tests for L{Task}.
    """
    @given(structure_and_messages=STRUCTURES_WITH_MESSAGES)
    def test_missing_action(self, structure_and_messages):
        """
        If we parse messages (in shuffled order) but a start message is
        missing then the structure is still deduced correctly from the
        remaining messages.
        """
        action_structure, messages = structure_and_messages
        assume(not isinstance(action_structure, unicode))

        # Remove first start message we encounter; since messages are
        # shuffled the location removed will differ over Hypothesis test
        # iterations:
        messages = messages[:]
        for i, message in enumerate(messages):
            if message[TASK_LEVEL_FIELD][-1] == 1:  # start message
                del messages[i]
                break

        task = Task()
        for message in messages:
            task = task.add(message)
        parsed_structure = ActionStructure.from_written(task.root())

        # We expect the action with missing start message to otherwise
        # be parsed correctly:
        self.assertEqual(parsed_structure, action_structure)

    @given(structure_and_messages=STRUCTURES_WITH_MESSAGES)
    def test_parse_from_random_order(self, structure_and_messages):
        """
        If we shuffle messages and parse them the parser builds a tree of
        actions that is the same as the one used to generate the messages.

        Shuffled messages means we have to deal with (temporarily) missing
        information sufficiently well to be able to parse correctly once
        the missing information arrives.
        """
        action_structure, messages = structure_and_messages

        task = Task()
        for message in messages:
            task = task.add(message)

        # Assert parsed structure matches input structure:
        parsed_structure = ActionStructure.from_written(task.root())
        self.assertEqual(parsed_structure, action_structure)

    @given(structure_and_messages=STRUCTURES_WITH_MESSAGES)
    def test_is_complete(self, structure_and_messages):
        """
        ``Task.is_complete()`` only returns true when all messages within the
        tree have been delivered.
        """
        action_structure, messages = structure_and_messages

        task = Task()
        completed = []
        for message in messages:
            task = task.add(message)
            completed.append(task.is_complete())

        self.assertEqual(completed,
                         [False for m in messages[:-1]] + [True])

    def test_parse_contents(self):
        """
        L{{Task.add}} parses the contents of the messages it receives.
        """
        logger = MemoryLogger()
        with start_action(logger, action_type="xxx", y=123) as ctx:
            Message.new(message_type="zzz", z=4).write(logger)
            ctx.add_success_fields(foo=[1, 2])
        messages = logger.messages
        expected = WrittenAction.from_messages(
            WrittenMessage.from_dict(messages[0]),
            [WrittenMessage.from_dict(messages[1])],
            WrittenMessage.from_dict(messages[2]))

        task = Task()
        for message in messages:
            task = task.add(message)
        self.assertEqual(task.root(), expected)


class ParserTests(TestCase):
    """
    Tests for L{Parser}.
    """
    @given(structure_and_messages1=STRUCTURES_WITH_MESSAGES,
           structure_and_messages2=STRUCTURES_WITH_MESSAGES,
           structure_and_messages3=STRUCTURES_WITH_MESSAGES)
    def test_parse_into_tasks(self, structure_and_messages1,
                              structure_and_messages2,
                              structure_and_messages3):
        """
        Adding messages to a L{Parser} parses them into a L{Task} instances.
        """
        _, messages1 = structure_and_messages1
        _, messages2 = structure_and_messages2
        _, messages3 = structure_and_messages3
        all_messages = (messages1, messages2, messages3)
        # Need unique UUIDs per task:
        assume(len(set(m[0][TASK_UUID_FIELD] for m in all_messages)) == 3)

        def parse_all(messages):
            task = Task()
            for message in messages:
                task = task.add(message)
            return task

        parser = Parser()
        all_tasks = []
        for message in chain(*izip_longest(*all_messages)):
            if message is not None:
                completed_tasks, parser = parser.add(message)
                all_tasks.extend(completed_tasks)

        self.assertItemsEqual(
            all_tasks, [parse_all(msgs) for msgs in all_messages])
