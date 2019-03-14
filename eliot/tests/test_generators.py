"""
Tests for L{eliot._generators}.
"""

from __future__ import unicode_literals, absolute_import

from pprint import pformat
from unittest import TestCase

from eliot import (
    Message,
    start_action,
)
from ..testing import (
    capture_logging,
    assertHasAction,
)

from .. import (
    use_generator_context,
    eliot_friendly_generator_function,
)
from .._action import _context


def assert_expected_action_tree(testcase, logger, expected_action_type, expected_type_tree):
    """
    Assert that a logger has a certain logged action with certain children.

    @see: L{assert_generator_logs_action_tree}
    """
    logged_action = assertHasAction(
        testcase,
        logger,
        expected_action_type,
        True,
    )
    type_tree = logged_action.type_tree()
    testcase.assertEqual(
        {expected_action_type: expected_type_tree},
        type_tree,
        "Logger had messages:\n{}".format(pformat(logger.messages, indent=4)),
    )


def assert_generator_logs_action_tree(testcase, generator_function, logger, expected_action_type, expected_type_tree):
    """
    Assert that exhausting a generator from the given function logs an action
    of the given type with children matching the given type tree.

    @param testcase: A test case instance to use to make assertions.
    @type testcase: L{unittest.TestCase}

    @param generator_function: A no-argument callable that returns a generator
        to be exhausted.

    @param logger: A logger to inspect for logged messages.
    @type logger: L{MemoryLogger}

    @param expected_action_type: An action type which should be logged by the
        generator.
    @type expected_action_type: L{unicode}

    @param expected_type_tree: The types of actions and messages which should
        be logged beneath the expected action.  The structure of this value
        matches the structure returned by L{LoggedAction.type_tree}.
    @type expected_type_tree: L{list}
    """
    list(eliot_friendly_generator_function(generator_function)())
    assert_expected_action_tree(
        testcase,
        logger,
        expected_action_type,
        expected_type_tree,
    )


class EliotFriendlyGeneratorFunctionTests(TestCase):
    """
    Tests for L{eliot_friendly_generator_function}.
    """
    # Get our custom assertion failure messages *and* the standard ones.
    longMessage = True

    def setUp(self):
        use_generator_context()

        def cleanup():
            _context.get_sub_context = lambda: None
        self.addCleanup(cleanup)

    @capture_logging(None)
    def test_yield_none(self, logger):
        @eliot_friendly_generator_function
        def g():
            Message.log(message_type=u"hello")
            yield
            Message.log(message_type=u"goodbye")

        with start_action(action_type=u"the-action"):
            list(g())

        assert_expected_action_tree(
            self,
            logger,
            u"the-action",
            [u"hello", u"yielded", u"goodbye"],
        )

    @capture_logging(None)
    def test_yield_value(self, logger):
        expected = object()

        @eliot_friendly_generator_function
        def g():
            Message.log(message_type=u"hello")
            yield expected
            Message.log(message_type=u"goodbye")

        with start_action(action_type=u"the-action"):
            self.assertEqual([expected], list(g()))

        assert_expected_action_tree(
            self,
            logger,
            u"the-action",
            [u"hello", u"yielded", u"goodbye"],
        )

    @capture_logging(None)
    def test_yield_inside_another_action(self, logger):
        @eliot_friendly_generator_function
        def g():
            Message.log(message_type=u"a")
            with start_action(action_type=u"confounding-factor"):
                Message.log(message_type=u"b")
                yield None
                Message.log(message_type=u"c")
            Message.log(message_type=u"d")

        with start_action(action_type=u"the-action"):
            list(g())

        assert_expected_action_tree(
            self,
            logger,
            u"the-action",
            [u"a",
             {u"confounding-factor": [u"b", u"yielded", u"c"]},
             u"d",
            ],
        )

    @capture_logging(None)
    def test_yield_inside_nested_actions(self, logger):
        @eliot_friendly_generator_function
        def g():
            Message.log(message_type=u"a")
            with start_action(action_type=u"confounding-factor"):
                Message.log(message_type=u"b")
                yield None
                with start_action(action_type=u"double-confounding-factor"):
                    yield None
                    Message.log(message_type=u"c")
                Message.log(message_type=u"d")
            Message.log(message_type=u"e")

        with start_action(action_type=u"the-action"):
            list(g())

        assert_expected_action_tree(
            self,
            logger,
            u"the-action", [
                u"a",
                {u"confounding-factor": [
                    u"b",
                    u"yielded",
                    {u"double-confounding-factor": [
                        u"yielded",
                        u"c",
                    ]},
                    u"d",
                ]},
                u"e",
            ],
        )

    @capture_logging(None)
    def test_generator_and_non_generator(self, logger):
        @eliot_friendly_generator_function
        def g():
            Message.log(message_type=u"a")
            yield
            with start_action(action_type=u"action-a"):
                Message.log(message_type=u"b")
                yield
                Message.log(message_type=u"c")

            Message.log(message_type=u"d")
            yield

        with start_action(action_type=u"the-action"):
            generator = g()
            next(generator)
            Message.log(message_type=u"0")
            next(generator)
            Message.log(message_type=u"1")
            next(generator)
            Message.log(message_type=u"2")
            self.assertRaises(StopIteration, lambda: next(generator))

        assert_expected_action_tree(
            self,
            logger,
            u"the-action", [
                u"a",
                u"yielded",
                u"0",
                {
                    u"action-a": [
                        u"b",
                        u"yielded",
                        u"c",
                    ],
                },
                u"1",
                u"d",
                u"yielded",
                u"2",
            ],
        )

    @capture_logging(None)
    def test_concurrent_generators(self, logger):
        @eliot_friendly_generator_function
        def g(which):
            Message.log(message_type=u"{}-a".format(which))
            with start_action(action_type=which):
                Message.log(message_type=u"{}-b".format(which))
                yield
                Message.log(message_type=u"{}-c".format(which))
            Message.log(message_type=u"{}-d".format(which))

        gens = [g(u"1"), g(u"2")]
        with start_action(action_type=u"the-action"):
            while gens:
                for g in gens[:]:
                    try:
                        next(g)
                    except StopIteration:
                        gens.remove(g)

        assert_expected_action_tree(
            self,
            logger,
            u"the-action", [
                u"1-a",
                {u"1": [
                    u"1-b",
                    u"yielded",
                    u"1-c",
                ]},
                u"2-a",
                {u"2": [
                    u"2-b",
                    u"yielded",
                    u"2-c",
                ]},
                u"1-d",
                u"2-d",
            ],
        )

    @capture_logging(None)
    def test_close_generator(self, logger):
        @eliot_friendly_generator_function
        def g():
            Message.log(message_type=u"a")
            try:
                yield
                Message.log(message_type=u"b")
            finally:
                Message.log(message_type=u"c")


        with start_action(action_type=u"the-action"):
            gen = g()
            next(gen)
            gen.close()

        assert_expected_action_tree(
            self,
            logger,
            u"the-action", [
                u"a",
                u"yielded",
                u"c",
            ],
        )

    @capture_logging(None)
    def test_nested_generators(self, logger):
        @eliot_friendly_generator_function
        def g(recurse):
            with start_action(action_type=u"a-recurse={}".format(recurse)):
                Message.log(message_type=u"m-recurse={}".format(recurse))
                if recurse:
                    set(g(False))
                else:
                    yield

        with start_action(action_type=u"the-action"):
            set(g(True))

        assert_expected_action_tree(
            self,
            logger,
            u"the-action", [{
                u"a-recurse=True": [
                    u"m-recurse=True", {
                        u"a-recurse=False": [
                            u"m-recurse=False",
                            u"yielded",
                        ],
                    },
                ],
            }],
        )
