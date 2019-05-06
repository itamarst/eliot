"""Tests for eliot.dask."""

from unittest import TestCase, skipUnless

from ..testing import capture_logging, LoggedAction, LoggedMessage
from .. import start_action, Message

try:
    import dask
    from dask.bag import from_sequence
except ImportError:
    dask = None
else:
    from ..dask import compute_with_trace, _RunWithEliotContext, _add_logging


@skipUnless(dask, "Dask not available.")
class DaskTests(TestCase):
    """Tests for end-to-end functionality."""

    def setUp(self):
        dask.config.set(scheduler="threading")

    def test_compute(self):
        """compute_with_trace() runs the same logic as compute()."""
        bag = from_sequence([1, 2, 3])
        bag = bag.map(lambda x: x * 7).map(lambda x: x * 4)
        bag = bag.fold(lambda x, y: x + y)
        self.assertEqual(dask.compute(bag), compute_with_trace(bag))

    @capture_logging(None)
    def test_logging(self, logger):
        """compute_with_trace() preserves Eliot context."""

        def mult(x):
            Message.log(message_type="mult")
            return x * 4

        def summer(x, y):
            Message.log(message_type="finally")
            return x + y

        bag = from_sequence([1, 2])
        bag = bag.map(mult).fold(summer)
        with start_action(action_type="act1"):
            compute_with_trace(bag)

        [logged_action] = LoggedAction.ofType(logger.messages, "act1")
        self.assertEqual(
            logged_action.type_tree(),
            {
                "act1": [
                    {
                        "dask:compute": [
                            {"eliot:remote_task": ["dask:task", "mult"]},
                            {"eliot:remote_task": ["dask:task", "mult"]},
                            {"eliot:remote_task": ["dask:task", "finally"]},
                        ]
                    }
                ]
            },
        )

        # Make sure dependencies are tracked:
        mult1_msg, mult2_msg, final_msg = LoggedMessage.ofType(
            logger.messages, "dask:task"
        )
        self.assertEqual(
            sorted(final_msg.message["dependencies"]),
            sorted([mult1_msg.message["key"], mult2_msg.message["key"]]),
        )

        # Make sure dependencies are logically earlier in the logs:
        self.assertTrue(
            mult1_msg.message["task_level"] < final_msg.message["task_level"]
        )
        self.assertTrue(
            mult2_msg.message["task_level"] < final_msg.message["task_level"]
        )


@skipUnless(dask, "Dask not available.")
class AddLoggingTests(TestCase):
    """Tests for _add_logging()."""

    def test_add_logging_to_full_graph(self):
        """_add_logging() recreates Dask graph with wrappers."""
        bag = from_sequence([1, 2, 3])
        bag = bag.map(lambda x: x * 7).map(lambda x: x * 4)
        bag = bag.fold(lambda x, y: x + y)
        graph = bag.__dask_graph__()

        # Add logging:
        with start_action(action_type="bleh"):
            logging_added = _add_logging(graph)

        # Ensure resulting graph hasn't changed substantively:
        logging_removed = {}
        for key, value in logging_added.items():
            if callable(value[0]):
                func, args = value[0], value[1:]
                self.assertIsInstance(func, _RunWithEliotContext)
                value = (func.func,) + args
            logging_removed[key] = value

        self.assertEqual(logging_removed, graph)
