"""
Tests for L{eliot.twisted}.
"""

from __future__ import absolute_import, unicode_literals

from unittest import TestCase

from twisted.internet.defer import Deferred

from ..twisted import DeferredContext, AlreadyFinished


class DeferredContextTests(TestCase):
    """
    Tests for L{DeferredContext}.
    """
    def test_result(self):
        """
        The passed-in L{Deferred} is available as the L{DeferredContext}'s
        C{result} attribute.
        """
        result = Deferred()
        context = DeferredContext(result)
        self.assertIs(context.result, result)


    def test_addCallbacksCallbackToDeferred(self):
        """
        L{DeferredContext.addCallbacks} passes the given callback and its
        corresponding arguments to the wrapped L{Deferred}'s
        C{addCallbacks}.
        """
        called = []
        def f(value, x, y):
            called.append((value, x, y))
        result = Deferred()
        context = DeferredContext(result)
        context.addCallbacks(f, lambda x: None, (1,), {"y": 2})
        result.callback(0)
        self.assertEqual(called, [(0, 1, 2)])


    def test_addCallbacksErrbackToDeferred(self):
        """
        L{DeferredContext.addCallbacks} passes the given errback and its
        corresponding arguments to the wrapped L{Deferred}'s
        C{addCallbacks}.
        """
        called = []
        def f(value, x, y):
            value.trap(RuntimeError)
            called.append((x, y))
        result = Deferred()
        context = DeferredContext(result)
        context.addCallbacks(lambda x: None, f, None, None, (1,), {"y": 2})
        result.errback(RuntimeError())
        self.assertEqual(called, [(1, 2)])
