"""
Tests for L{eliot._parse}.
"""

from unittest import TestCase
from random import shuffle

from hypothesis import strategies, strategy, example

from pyrsistent import PClass, field, pvector_field

from .. import start_action, Message
from ..testing import capture_logging
from .._parse import Task
from .._message import WrittenMessage


class StubAction(PClass):
    type = field(type=unicode, mandatory=True)
    children = pvector_field(("StubAction", unicode), mandatory=True)

    @classmethod
    def _from_tree(cls, tree_or_message):
        if isinstance(tree_or_message, list):
            return StubAction(
                type=TYPES.example(),
                children=[StubAction._from_tree(o) for o in tree_or_message])
        else:
            return tree_or_message

    @classmethod
    def from_written(cls, written):
        if isinstance(written, WrittenMessage):
            return written.message_type
        else:  # WrittenAction
            return StubAction(
                type=written.action_type,
                children=[StubAction.from_written(o) for o in written.children]
                + [written.end_message])

    @classmethod
    def to_eliot(cls, stub_or_message):
        if isinstance(stub_or_message, cls):
            action = stub_or_message
            with start_action(action_type=action.type):
                for child in action.children:
                    cls.to_eliot(child)
        else:
            Message.log(message_type=stub_or_message)


TYPES = strategies.text(min_size=1, average_size=3, alphabet=u"CGAT")
TASKS = strategies.recursive(
    strategies.text(min_size=1, average_size=3, alphabet=u"CGAT"),
    strategies.lists, max_leaves=5).map(StubAction.from_tree)


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
    @strategy(task_structure=TASKS)
    @example(task_structure=u"standalone_message")
    @example(task_structure=[])
    @capture_logging(None)
    def test_parse_from_random_order(self, logger, task_structure):
        StubAction.to_eliot(task_structure)
        messages = logger.messages
        order = range(len(messages))
        shuffle(order)
        task = Task.from_messages([messages[i] for i in order])
        parsed_structure = StubAction.from_written(task.root())
        self.assertEqual(parsed_structure, task_structure,
                         "Order: {}".format(order))
