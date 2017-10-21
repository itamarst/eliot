"""
Tests for coroutines.

Imported into test_coroutine.py when running tests under Python 3.6; in earlier
versions of Python this code is a syntax error.
"""

import asyncio
from unittest import TestCase

from ..testing import assertContainsFields, capture_logging
from .._parse import Parser
from .. import Message, start_action


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


class CoroutineTests(TestCase):
    """
    Tests for coroutines.
    """
    @capture_logging(None)
    def test_coroutine_vs_main_thread_context(self, logger):
        """
        A coroutine has a different Eliot context than the thread that runs the
        event loop.
        """
        with start_action(action_type="eventloop"):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(standalone_coro())
            loop.close()
        trees = Parser.parse_stream(logger.messages)
        self.assertEqual(
            sorted([(t.root().action_type, t.root().children) for t in trees]),
            [("eventloop", []), ("standalone", [])])

    @capture_logging(None)
    def test_multiple_coroutines_contexts(self, logger):
        """
        Each coroutine has its own Eliot context.
        """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(calling_coro())
        loop.close()
        trees = Parser.parse_stream(logger.messages)
        self.assertEqual(
            sorted([(t.root().action_type, t.root().children) for t in trees]),
            [("calling", []), ("standalone", [])])
