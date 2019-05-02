"""
Tests for coroutines.

Imported into test_coroutine.py when running tests under Python 3.5 or later;
in earlier versions of Python this code is a syntax error.
"""

import asyncio
from unittest import TestCase

from ..testing import capture_logging
from ..parse import Parser
from .. import start_action


async def standalone_coro():
    """
    Log a message inside a new coroutine.
    """
    await asyncio.sleep(0.1)
    with start_action(action_type="standalone"):
        pass


async def calling_coro():
    """
    Log an action inside a coroutine, and call another coroutine.
    """
    with start_action(action_type="calling"):
        await standalone_coro()


def run_coroutines(*async_functions):
    """
    Run a coroutine until it finishes.
    """
    loop = asyncio.get_event_loop()
    futures = [asyncio.ensure_future(f()) for f in async_functions]

    async def wait_for_futures():
        for future in futures:
            await future
    loop.run_until_complete(wait_for_futures())


class CoroutineTests(TestCase):
    """
    Tests for coroutines.
    """
    @capture_logging(None)
    def test_multiple_coroutines_contexts(self, logger):
        """
        Each top-level coroutine has its own Eliot logging context.
        """
        async def waiting_coro():
            with start_action(action_type="waiting"):
                await asyncio.sleep(0.5)

        run_coroutines(waiting_coro, standalone_coro)
        trees = Parser.parse_stream(logger.messages)
        self.assertEqual(
            sorted([(t.root().action_type, t.root().children) for t in trees]),
            [("standalone", []), ("waiting", [])])

    @capture_logging(None)
    def test_await_inherits_coroutine_contexts(self, logger):
        """
        awaited coroutines inherit the logging context.
        """
        run_coroutines(calling_coro)
        [tree] = Parser.parse_stream(logger.messages)
        root = tree.root()
        [child] = root.children
        self.assertEqual(
            (root.action_type, child.action_type, child.children),
            ("calling", "standalone", []))

    @capture_logging(None)
    def test_interleaved_coroutines(self, logger):
        """
        start_action() started in one coroutine doesn't impact another in a
        different coroutine.
        """
        async def coro_sleep(delay, action_type):
            with start_action(action_type=action_type):
                await asyncio.sleep(delay)

        async def main():
            with start_action(action_type="main"):
                f1 = asyncio.ensure_future(coro_sleep(1, "a"))
                f2 = asyncio.ensure_future(coro_sleep(0.5, "b"))
                await f1
                await f2

        run_coroutines(main)
        [tree] = list(Parser.parse_stream(logger.messages))
        root = tree.root()
        self.assertEqual(root.action_type, "main")
        self.assertEqual(sorted([c.action_type for c in root.children]), ["a", "b"])
