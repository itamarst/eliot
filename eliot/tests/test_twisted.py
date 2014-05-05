"""
Tests for L{eliot.twisted}.
"""

from __future__ import absolute_import, unicode_literals

from unittest import TestCase

from twisted.internet.defer import Deferred

from ..twisted import DeferredContext, AlreadyFinished, _passthrough


class PassthroughTests(TestCase):
    """
    Tests for L{_passthrough}.
    """
    def test_passthrough(self):
        """
        L{_passthrough} returns the passed-in value.
        """
        obj = object()
        self.assertIs(obj, _passthrough(obj))



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


    def test_addCallbacksReturnSelf(self):
        """
        L{DeferredContext.addCallbacks} returns the L{DeferredContext}.
        """
        result = Deferred()
        context = DeferredContext(result)
        self.assertIs(context, context.addCallbacks(
            lambda x: None, lambda x: None))


    def test_addCallbackCallsAddCallbacks(self):
        """
        L{DeferredContext.addCallback} passes its arguments on to
        L{DeferredContext.addCallbacks}.
        """
        result = Deferred()
        context = DeferredContext(result)
        called = []
        def addCallbacks(callback, errback,
                         callbackArgs=None, callbackKeywords=None,
                         errbackArgs=None, errbackKeywords=None):
            called.append((callback, errback, callbackArgs, callbackKeywords,
                           errbackArgs, errbackKeywords))
        context.addCallbacks = addCallbacks
        f = lambda x, y, z: None
        context.addCallback(f, 2, z=3)
        self.assertEqual(called, [(f, _passthrough, (2,), {"z": 3}, None, None)])


    def test_addCallbackReturnsSelf(self):
        """
        L{DeferredContext.addCallback} returns the L{DeferredContext}.
        """
        result = Deferred()
        context = DeferredContext(result)
        self.assertIs(context, context.addCallback(lambda x: None))
