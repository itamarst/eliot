"""
Tests for coroutines.

Imported into test_coroutine.py when running tests under Python 3.6; in earlier
versions of Python this code is a syntax error.
"""

import asyncio
from unittest import TestCase

from ..testing import capture_logging
from .._parse import Parser
from .. import start_action
from .._action import _ExecutionContext


async def standalone_coro():
    """
    Log a message inside a new coroutine.
    """
    with start_action(action_type="standalone"):
        pass


async def calling_coro():
    """
    Log an action inside a coroutine, and call another coroutine.
    """
    with start_action(action_type="calling"):
        await standalone_coro()


def run_coroutine(async_function):
    """
    Run a coroutine until it finishes.
    """
    loop = asyncio.new_event_loop()
    loop.run_until_complete(async_function())
    loop.close()


class CoroutineTests(TestCase):
    """
    Tests for coroutines.
    """
    @capture_logging(None)
    def test_coroutine_vs_main_thread_context(self, logger):
        """
        A coroutine has a different Eliot logging context than the thread that
        runs the event loop.
        """
        with start_action(action_type="eventloop"):
            run_coroutine(standalone_coro)
        trees = Parser.parse_stream(logger.messages)
        self.assertEqual(
            sorted([(t.root().action_type, t.root().children) for t in trees]),
            [("eventloop", []), ("standalone", [])])

    @capture_logging(None)
    def test_multiple_coroutines_contexts(self, logger):
        """
        Each coroutine has its own Eliot logging context.
        """
        run_coroutine(calling_coro)
        trees = Parser.parse_stream(logger.messages)
        self.assertEqual(
            sorted([(t.root().action_type, t.root().children) for t in trees]),
            [("calling", []), ("standalone", [])])


class ContextTests(TestCase):
    """
    Tests for coroutine support in ``eliot._action.ExecutionContext``.
    """
    def test_coroutine_vs_main_thread_context(self):
        """
        A coroutine has a different Eliot context than the thread that runs the
        event loop.
        """
        ctx = _ExecutionContext()
        current_context = []

        async def coro():
            current_context.append(("coro", ctx.current()))
            ctx.push("A")
            current_context.append(("coro", ctx.current()))

        ctx.push("B")
        current_context.append(("main", ctx.current()))
        run_coroutine(coro)
        current_context.append(("main", ctx.current()))
        self.assertEqual(
            current_context,
            [("main", "B"), ("coro", None), ("coro", "A"), ("main", "B")])

    def test_multiple_coroutines_contexts(self):
        """
        Each coroutine has its own Eliot separate context.
        """
        ctx = _ExecutionContext()
        current_context = []

        async def coro2():
            current_context.append(("coro2", ctx.current()))
            ctx.push("B")
            current_context.append(("coro2", ctx.current()))

        async def coro():
            current_context.append(("coro", ctx.current()))
            ctx.push("A")
            current_context.append(("coro", ctx.current()))
            await coro2()
            current_context.append(("coro", ctx.current()))

        run_coroutine(coro)
        self.assertEqual(
            current_context,
            [("coro", None), ("coro", "A"), ("coro2", None),
             ("coro2", "B"), ("coro", "A")])
