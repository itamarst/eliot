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


class ActionStructure(PClass):
    type = field(type=unicode, mandatory=True)
    children = pvector_field(("StubAction", unicode), mandatory=True)

    @classmethod
    def _from_tree(cls, tree_or_message):
        if isinstance(tree_or_message, list):
            return cls(
                type=TYPES.example(),
                children=[cls._from_tree(o) for o in tree_or_message])
        else:
            return tree_or_message

    @classmethod
    def from_written(cls, written):
        if isinstance(written, WrittenMessage):
            return written.message_type
        else:  # WrittenAction
            return cls(
                type=written.action_type,
                children=[cls.from_written(o) for o in written.children]
                + [written.end_message])

    @classmethod
    def to_eliot(cls, structure_or_message):
        if isinstance(structure_or_message, cls):
            action = structure_or_message
            with start_action(action_type=action.type):
                for child in action.children:
                    cls.to_eliot(child)
        else:
            Message.log(message_type=structure_or_message)


TYPES = strategies.text(min_size=1, average_size=3, alphabet=u"CGAT")
ACTION_STRUCTURES = strategies.recursive(
    strategies.text(min_size=1, average_size=3, alphabet=u"CGAT"),
    strategies.lists, max_leaves=5).map(ActionStructure.from_tree)


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
    @strategy(action_structure=ACTION_STRUCTURES)
    @example(action_structure=u"standalone_message")
    @capture_logging(None)
    def test_parse_from_random_order(self, logger, action_structure):
        # Create Eliot messages for given tree of actions and messages:
        ActionStructure.to_eliot(action_structure)
        messages = logger.messages

        # Parse resulting message dicts in random order:
        order = range(len(messages))
        shuffle(order)
        task = Task.create(messages[order[0]])
        for index in order[1:]:
            task = task.add(messages[index])

        # Assert parsed structure matches input structure:
        parsed_structure = ActionStructure.from_written(task.root())
        self.assertEqual(parsed_structure, action_structure,
                         "Order: {}".format(order))
