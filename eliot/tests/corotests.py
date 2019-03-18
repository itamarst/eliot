"""
Tests for coroutines.

Imported into test_coroutine.py when running tests under Python 3.5 or later;
in earlier versions of Python this code is a syntax error.
"""

import asyncio
from threading import Thread
from unittest import TestCase

from ..testing import capture_logging
from ..parse import Parser
from .. import start_action
from .._action import _context_owner, use_asyncio_context
from .._asyncio import AsyncioExecutionContext


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
    def setUp(self):
        self.addCleanup(_context_owner.reset)
        use_asyncio_context()

    @capture_logging(None)
    def test_coroutine_vs_main_thread_context(self, logger):
        """
        A coroutine has a different Eliot logging context than the thread that
        runs the event loop.
        """
        with start_action(action_type="eventloop"):
            run_coroutines(standalone_coro)
        trees = Parser.parse_stream(logger.messages)
        self.assertEqual(
            sorted([(t.root().action_type, t.root().children) for t in trees]),
            [("eventloop", []), ("standalone", [])])

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


class ContextTests(TestCase):
    """
    Tests for coroutine support in ``eliot._action.ExecutionContext``.
    """
    def test_threadSafety(self):
        """
        Each thread gets its own execution context even when using asyncio
        contexts.
        """
        ctx = AsyncioExecutionContext()
        first = object()
        ctx.push(first)

        second = object()
        valuesInThread = []

        def inthread():
            ctx.push(second)
            valuesInThread.append(ctx.current())

        thread = Thread(target=inthread)
        thread.start()
        thread.join()
        # Neither thread was affected by the other:
        self.assertEqual(valuesInThread, [second])
        self.assertIs(ctx.current(), first)

    def test_coroutine_vs_main_thread_context(self):
        """
        A coroutine has a different Eliot context than the thread that runs the
        event loop.
        """
        ctx = AsyncioExecutionContext()
        current_context = []

        async def coro():
            current_context.append(("coro", ctx.current()))
            ctx.push("A")
            current_context.append(("coro", ctx.current()))

        ctx.push("B")
        current_context.append(("main", ctx.current()))
        run_coroutines(coro)
        current_context.append(("main", ctx.current()))
        self.assertEqual(
            current_context,
            [("main", "B"), ("coro", None), ("coro", "A"), ("main", "B")])

    def test_coroutine_vs_main_thread_context_different_thread(self):
        """
        A coroutine has a different Eliot context than the thread that runs the
        event loop, when run in different thread than the one where the context
        was created.
        """
        # Create context in one thread:
        ctx = AsyncioExecutionContext()
        current_context = []

        # Run asyncio event loop and coroutines in a different thread:
        def run():
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)

            async def coro():
                current_context.append(("coro", ctx.current()))
                ctx.push("A")
                current_context.append(("coro", ctx.current()))

            ctx.push("B")
            current_context.append(("main", ctx.current()))
            run_coroutines(coro)
            current_context.append(("main", ctx.current()))

        thread = Thread(target=run)
        thread.start()
        thread.join()

        self.assertEqual(
            current_context,
            [("main", "B"), ("coro", None), ("coro", "A"), ("main", "B")])

    def test_multiple_coroutines_contexts(self):
        """
        Each top-level ("Task") coroutine has its own Eliot separate context.
        """
        ctx = AsyncioExecutionContext()
        current_context = []

        async def coro2():
            current_context.append(("coro2", ctx.current()))
            ctx.push("B")
            await asyncio.sleep(1)
            current_context.append(("coro2", ctx.current()))

        async def coro():
            current_context.append(("coro", ctx.current()))
            await asyncio.sleep(0.5)
            current_context.append(("coro", ctx.current()))
            ctx.push("A")
            current_context.append(("coro", ctx.current()))

        run_coroutines(coro, coro2)
        self.assertEqual(
            current_context,
            [("coro", None), ("coro2", None), ("coro", None),
             ("coro", "A"), ("coro2", "B")])

    def test_await_inherits_coroutine_context(self):
        """
        A sub-coroutine (scheduled with await) inherits the parent coroutine's
        context.
        """
        ctx = AsyncioExecutionContext()
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

        run_coroutines(coro)
        self.assertEqual(
            current_context,
            [("coro", None), ("coro", "A"), ("coro2", "A"),
             ("coro2", "B"), ("coro", "B")])
