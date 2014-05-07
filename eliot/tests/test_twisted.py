"""
Tests for L{eliot.twisted}.
"""

from __future__ import absolute_import, unicode_literals, print_function

from functools import wraps

from twisted.internet.defer import Deferred, succeed, fail
from twisted.trial.unittest import TestCase
from twisted.python.failure import Failure

from ..twisted import DeferredContext, AlreadyFinished, _passthrough
from .._action import startAction, currentAction, Action
from .._output import MemoryLogger
from ..testing import assertContainsFields


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



def withActionContext(f):
    """
    Decorator that calls a function with an action context.

    @param f: A function.
    """
    logger = MemoryLogger()
    action = startAction(logger, "test")
    @wraps(f)
    def test(self):
        with action.context():
            return f(self)
    return test



class DeferredContextTests(TestCase):
    """
    Tests for L{DeferredContext}.
    """
    def test_requireContext(self):
        """
        L{DeferredContext} raises a L{RuntimeError} if it is called without an
        action context.
        """
        self.assertRaises(RuntimeError, DeferredContext, Deferred())


    @withActionContext
    def test_result(self):
        """
        The passed-in L{Deferred} is available as the L{DeferredContext}'s
        C{result} attribute.
        """
        result = Deferred()
        context = DeferredContext(result)
        self.assertIs(context.result, result)


    @withActionContext
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


    @withActionContext
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


    @withActionContext
    def test_addCallbacksReturnSelf(self):
        """
        L{DeferredContext.addCallbacks} returns the L{DeferredContext}.
        """
        result = Deferred()
        context = DeferredContext(result)
        self.assertIs(context, context.addCallbacks(
            lambda x: None, lambda x: None))


    def test_addCallbacksCallbackContext(self):
        """
        L{DeferedContext.addCallbacks} adds a callback that runs in context of
        action that the L{DeferredContext} was created with.
        """
        logger = MemoryLogger()
        action1 = startAction(logger, "test")
        action2 = startAction(logger, "test")
        context = []
        d = succeed(None)
        with action1.context():
            d = DeferredContext(d)
            with action2.context():
                d.addCallbacks(lambda x: context.append(currentAction()),
                               lambda x: x)
        self.assertEqual(context, [action1])


    def test_addCallbacksErrbackContext(self):
        """
        L{DeferedContext.addCallbacks} adds an errback that runs in context of
        action that the L{DeferredContext} was created with.
        """
        logger = MemoryLogger()
        action1 = startAction(logger, "test")
        action2 = startAction(logger, "test")
        context = []
        d = fail(RuntimeError())
        with action1.context():
            d = DeferredContext(d)
            with action2.context():
                d.addCallbacks(lambda x: x,
                               lambda x: context.append(currentAction()))
        self.assertEqual(context, [action1])


    @withActionContext
    def test_addCallbacksCallbackResult(self):
        """
        A callback added with DeferredContext.addCallbacks has its result passed
        on to the next callback.
        """
        d = succeed(0)
        d = DeferredContext(d)
        d.addCallbacks(lambda x: [x, 1], lambda x: x)
        self.assertEqual(self.successResultOf(d), [0, 1])


    @withActionContext
    def test_addCallbacksErrbackResult(self):
        """
        An errback added with DeferredContext.addCallbacks has its result passed
        on to the next callback.
        """
        exception = ZeroDivisionError()
        d = fail(exception)
        d = DeferredContext(d)
        d.addCallbacks(lambda x: x, lambda x: [x.value, 1])
        self.assertEqual(self.successResultOf(d), [exception, 1])


    def test_addActionFinishNoImmediateLogging(self):
        """
        L{DeferredContext.addActionFinish} does not log anything if the
        L{Deferred} hasn't fired yet.
        """
        d = Deferred()
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        with action.context():
            DeferredContext(d).addActionFinish()
        self.assertFalse(logger.messages)


    def test_addActionFinishSuccess(self):
        """
        When the L{Deferred} referred to by L{DeferredContext.addActionFinish}
        fires successfully, a finish message is logged.
        """
        d = Deferred()
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        with action.context():
            DeferredContext(d).addActionFinish()
        d.callback("result")
        assertContainsFields(self, logger.messages[0],
                             {"task_uuid": "uuid",
                              "task_level": "/1/",
                              "action_type": "sys:me",
                              "action_status": "succeeded"})


    def test_addActionFinishSuccessPassThrough(self):
        """
        L{DeferredContext.addActionFinish} passes through a successful result
        unchanged.
        """
        d = Deferred()
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        with action.context():
            DeferredContext(d).addActionFinish()
        d.callback("result")
        result = []
        d.addCallback(result.append)
        self.assertEqual(result, ["result"])


    def test_addActionFinishFailure(self):
        """
        When the L{Deferred} referred to in L{DeferredContext.addActionFinish}
        fires with an exception, a finish message is logged.
        """
        d = Deferred()
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        with action.context():
            DeferredContext(d).addActionFinish()
        exception = RuntimeError("because")
        d.errback(exception)
        assertContainsFields(self, logger.messages[0],
                             {"task_uuid": "uuid",
                              "task_level": "/1/",
                              "action_type": "sys:me",
                              "action_status": "failed",
                              "reason": "because",
                              "exception":
                              "%s.RuntimeError" % (RuntimeError.__module__,)})
        d.addErrback(lambda _: None) # don't let Failure go to Twisted logs


    def test_addActionFinishFailurePassThrough(self):
        """
        L{DeferredContext.addActionFinish} passes through a failed result
        unchanged.
        """
        d = Deferred()
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        with action.context():
            DeferredContext(d).addActionFinish()
        failure = Failure(RuntimeError())
        d.errback(failure)
        result = []
        d.addErrback(result.append)
        self.assertEqual(result, [failure])

    # XXX remaining tests:
    # After DeferredContext.addActionFinish is called, additional calls to addCallbacks result in AlreadyFinished exception.
    # addActionFinish returns the Deferred.

    # Having made sure DeferredContext.addCallbacks does the right thing
    # regarding action contexts, for addCallback/addErrback/addBoth we only
    # need to ensure that they call DeferredContext.addCallbacks.

    @withActionContext
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


    @withActionContext
    def test_addCallbackReturnsSelf(self):
        """
        L{DeferredContext.addCallback} returns the L{DeferredContext}.
        """
        result = Deferred()
        context = DeferredContext(result)
        self.assertIs(context, context.addCallback(lambda x: None))


    @withActionContext
    def test_addErrbackCallsAddCallbacks(self):
        """
        L{DeferredContext.addErrback} passes its arguments on to
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
        context.addErrback(f, 2, z=3)
        self.assertEqual(called, [(_passthrough, f, None, None, (2,), {"z": 3})])


    @withActionContext
    def test_addErrbackReturnsSelf(self):
        """
        L{DeferredContext.addErrback} returns the L{DeferredContext}.
        """
        result = Deferred()
        context = DeferredContext(result)
        self.assertIs(context, context.addErrback(lambda x: None))


    @withActionContext
    def test_addBothCallsAddCallbacks(self):
        """
        L{DeferredContext.addBoth} passes its arguments on to
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
        context.addBoth(f, 2, z=3)
        self.assertEqual(called, [(f, f, (2,), {"z": 3}, (2,), {"z": 3})])


    @withActionContext
    def test_addBothReturnsSelf(self):
        """
        L{DeferredContext.addBoth} returns the L{DeferredContext}.
        """
        result = Deferred()
        context = DeferredContext(result)
        self.assertIs(context, context.addBoth(lambda x: None))
