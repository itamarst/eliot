"""Tests for eliot.dask."""

from unittest import TestCase, skipUnless

from ..testing import capture_logging, LoggedAction, LoggedMessage
from .. import start_action, log_message

try:
    import dask
    from dask.bag import from_sequence
    from dask.distributed import Client
    import dask.dataframe as dd
    import pandas as pd
except ImportError:
    dask = None
else:
    from ..dask import (
        compute_with_trace,
        _RunWithEliotContext,
        _add_logging,
        persist_with_trace,
    )


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

    def test_future(self):
        """compute_with_trace() can handle Futures."""
        client = Client(processes=False)
        self.addCleanup(client.shutdown)
        [bag] = dask.persist(from_sequence([1, 2, 3]))
        bag = bag.map(lambda x: x * 5)
        result = dask.compute(bag)
        self.assertEqual(result, ([5, 10, 15],))
        self.assertEqual(result, compute_with_trace(bag))

    def test_persist_result(self):
        """persist_with_trace() runs the same logic as process()."""
        client = Client(processes=False)
        self.addCleanup(client.shutdown)
        bag = from_sequence([1, 2, 3])
        bag = bag.map(lambda x: x * 7)
        self.assertEqual(
            [b.compute() for b in dask.persist(bag)],
            [b.compute() for b in persist_with_trace(bag)],
        )

    def test_persist_pandas(self):
        """persist_with_trace() with a Pandas dataframe.

        This ensures we don't blow up, which used to be the case.
        """
        df = pd.DataFrame()
        df = dd.from_pandas(df, npartitions=1)
        persist_with_trace(df)

    @capture_logging(None)
    def test_persist_logging(self, logger):
        """persist_with_trace() preserves Eliot context."""

        def persister(bag):
            [bag] = persist_with_trace(bag)
            return dask.compute(bag)

        self.assert_logging(logger, persister, "dask:persist")

    @capture_logging(None)
    def test_compute_logging(self, logger):
        """compute_with_trace() preserves Eliot context."""
        self.assert_logging(logger, compute_with_trace, "dask:compute")

    def assert_logging(self, logger, run_with_trace, top_action_name):
        """Utility function for _with_trace() logging tests."""

        def mult(x):
            log_message(message_type="mult")
            return x * 4

        def summer(x, y):
            log_message(message_type="finally")
            return x + y

        bag = from_sequence([1, 2])
        bag = bag.map(mult).fold(summer)
        with start_action(action_type="act1"):
            run_with_trace(bag)

        [logged_action] = LoggedAction.ofType(logger.messages, "act1")
        self.assertEqual(
            logged_action.type_tree(),
            {
                "act1": [
                    {
                        top_action_name: [
                            {"eliot:remote_task": ["dask:task", "mult"]},
                            {"eliot:remote_task": ["dask:task", "mult"]},
                            {"eliot:remote_task": ["dask:task", "finally"]},
                        ]
                    }
                ]
            },
        )

        # Make sure dependencies are tracked:
        (
            mult1_msg,
            mult2_msg,
            final_msg,
        ) = LoggedMessage.ofType(logger.messages, "dask:task")
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

    maxDiff = None

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

    def test_add_logging_explicit(self):
        """_add_logging() on more edge cases of the graph."""

        def add(s):
            return s + "s"

        def add2(s):
            return s + "s"

        # b runs first, then d, then a and c.
        graph = {
            "a": "d",
            "d": [1, 2, (add, "b")],
            ("b", 0): 1,
            "c": (add2, "d"),
        }

        with start_action(action_type="bleh") as action:
            task_id = action.task_uuid
            self.assertEqual(
                _add_logging(graph),
                {
                    "d": [
                        1,
                        2,
                        (
                            _RunWithEliotContext(
                                task_id=task_id + "@/2",
                                func=add,
                                key="d",
                                dependencies=["b"],
                            ),
                            "b",
                        ),
                    ],
                    "a": "d",
                    ("b", 0): 1,
                    "c": (
                        _RunWithEliotContext(
                            task_id=task_id + "@/3",
                            func=add2,
                            key="c",
                            dependencies=["d"],
                        ),
                        "d",
                    ),
                },
            )
