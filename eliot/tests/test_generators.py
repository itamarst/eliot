"""
Tests for L{eliot._generators}.
"""


from pprint import pformat
from unittest import TestCase

from eliot import Message, start_action
from ..testing import capture_logging, assertHasAction

from .._generators import eliot_friendly_generator_function


def assert_expected_action_tree(
    testcase, logger, expected_action_type, expected_type_tree
):
    """
    Assert that a logger has a certain logged action with certain children.

    @see: L{assert_generator_logs_action_tree}
    """
    logged_action = assertHasAction(testcase, logger, expected_action_type, True)
    type_tree = logged_action.type_tree()
    testcase.assertEqual(
        {expected_action_type: expected_type_tree},
        type_tree,
        "Logger had messages:\n{}".format(pformat(logger.messages, indent=4)),
    )


def assert_generator_logs_action_tree(
    testcase, generator_function, logger, expected_action_type, expected_type_tree
):
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
        testcase, logger, expected_action_type, expected_type_tree
    )


class EliotFriendlyGeneratorFunctionTests(TestCase):
    """
    Tests for L{eliot_friendly_generator_function}.
    """

    # Get our custom assertion failure messages *and* the standard ones.
    longMessage = True

    @capture_logging(None)
    def test_yield_none(self, logger):
        @eliot_friendly_generator_function
        def g():
            Message.log(message_type="hello")
            yield
            Message.log(message_type="goodbye")

        g.debug = True  # output yielded messages

        with start_action(action_type="the-action"):
            list(g())

        assert_expected_action_tree(
            self, logger, "the-action", ["hello", "yielded", "goodbye"]
        )

    @capture_logging(None)
    def test_yield_value(self, logger):
        expected = object()

        @eliot_friendly_generator_function
        def g():
            Message.log(message_type="hello")
            yield expected
            Message.log(message_type="goodbye")

        g.debug = True  # output yielded messages

        with start_action(action_type="the-action"):
            self.assertEqual([expected], list(g()))

        assert_expected_action_tree(
            self, logger, "the-action", ["hello", "yielded", "goodbye"]
        )

    @capture_logging(None)
    def test_yield_inside_another_action(self, logger):
        @eliot_friendly_generator_function
        def g():
            Message.log(message_type="a")
            with start_action(action_type="confounding-factor"):
                Message.log(message_type="b")
                yield None
                Message.log(message_type="c")
            Message.log(message_type="d")

        g.debug = True  # output yielded messages

        with start_action(action_type="the-action"):
            list(g())

        assert_expected_action_tree(
            self,
            logger,
            "the-action",
            ["a", {"confounding-factor": ["b", "yielded", "c"]}, "d"],
        )

    @capture_logging(None)
    def test_yield_inside_nested_actions(self, logger):
        @eliot_friendly_generator_function
        def g():
            Message.log(message_type="a")
            with start_action(action_type="confounding-factor"):
                Message.log(message_type="b")
                yield None
                with start_action(action_type="double-confounding-factor"):
                    yield None
                    Message.log(message_type="c")
                Message.log(message_type="d")
            Message.log(message_type="e")

        g.debug = True  # output yielded messages

        with start_action(action_type="the-action"):
            list(g())

        assert_expected_action_tree(
            self,
            logger,
            "the-action",
            [
                "a",
                {
                    "confounding-factor": [
                        "b",
                        "yielded",
                        {"double-confounding-factor": ["yielded", "c"]},
                        "d",
                    ]
                },
                "e",
            ],
        )

    @capture_logging(None)
    def test_generator_and_non_generator(self, logger):
        @eliot_friendly_generator_function
        def g():
            Message.log(message_type="a")
            yield
            with start_action(action_type="action-a"):
                Message.log(message_type="b")
                yield
                Message.log(message_type="c")

            Message.log(message_type="d")
            yield

        g.debug = True  # output yielded messages

        with start_action(action_type="the-action"):
            generator = g()
            next(generator)
            Message.log(message_type="0")
            next(generator)
            Message.log(message_type="1")
            next(generator)
            Message.log(message_type="2")
            self.assertRaises(StopIteration, lambda: next(generator))

        assert_expected_action_tree(
            self,
            logger,
            "the-action",
            [
                "a",
                "yielded",
                "0",
                {"action-a": ["b", "yielded", "c"]},
                "1",
                "d",
                "yielded",
                "2",
            ],
        )

    @capture_logging(None)
    def test_concurrent_generators(self, logger):
        @eliot_friendly_generator_function
        def g(which):
            Message.log(message_type="{}-a".format(which))
            with start_action(action_type=which):
                Message.log(message_type="{}-b".format(which))
                yield
                Message.log(message_type="{}-c".format(which))
            Message.log(message_type="{}-d".format(which))

        g.debug = True  # output yielded messages

        gens = [g("1"), g("2")]
        with start_action(action_type="the-action"):
            while gens:
                for g in gens[:]:
                    try:
                        next(g)
                    except StopIteration:
                        gens.remove(g)

        assert_expected_action_tree(
            self,
            logger,
            "the-action",
            [
                "1-a",
                {"1": ["1-b", "yielded", "1-c"]},
                "2-a",
                {"2": ["2-b", "yielded", "2-c"]},
                "1-d",
                "2-d",
            ],
        )

    @capture_logging(None)
    def test_close_generator(self, logger):
        @eliot_friendly_generator_function
        def g():
            Message.log(message_type="a")
            try:
                yield
                Message.log(message_type="b")
            finally:
                Message.log(message_type="c")

        g.debug = True  # output yielded messages

        with start_action(action_type="the-action"):
            gen = g()
            next(gen)
            gen.close()

        assert_expected_action_tree(self, logger, "the-action", ["a", "yielded", "c"])

    @capture_logging(None)
    def test_nested_generators(self, logger):
        @eliot_friendly_generator_function
        def g(recurse):
            with start_action(action_type="a-recurse={}".format(recurse)):
                Message.log(message_type="m-recurse={}".format(recurse))
                if recurse:
                    set(g(False))
                else:
                    yield

        g.debug = True  # output yielded messages

        with start_action(action_type="the-action"):
            set(g(True))

        assert_expected_action_tree(
            self,
            logger,
            "the-action",
            [
                {
                    "a-recurse=True": [
                        "m-recurse=True",
                        {"a-recurse=False": ["m-recurse=False", "yielded"]},
                    ]
                }
            ],
        )
