"""
Tests for L{eliot.twisted}.
"""

from __future__ import absolute_import, unicode_literals, print_function

import traceback
import sys
import inspect
from functools import wraps
from pprint import pformat

try:
    from twisted.internet.defer import Deferred, succeed, fail
    from twisted.trial.unittest import TestCase
    from twisted.python.failure import Failure
    from twisted.python.log import LogPublisher, textFromEventDict
    from twisted.python import log as twlog
except ImportError:
    # Make tests not run at all.
    TestCase = object
else:
    # Make sure we always import this if Twisted is available, so broken
    # logwriter.py causes a failure:
    from ..twisted import (
        DeferredContext, AlreadyFinished, _passthrough, redirectLogsForTrial)

from .._action import startAction, currentAction, Action
from .._output import MemoryLogger, Logger
from .._message import Message
from ..testing import assertContainsFields
from .. import removeDestination, addDestination
from .._traceback import writeTraceback
from .common import FakeSys


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


    @withActionContext
    def test_addActionFinishRaisesAfterAddActionFinish(self):
        """
        After L{DeferredContext.addActionFinish} is called, additional calls to
        L{DeferredContext.addActionFinish} result in a L{AlreadyFinished}
        exception.
        """
        d = DeferredContext(Deferred())
        d.addActionFinish()
        self.assertRaises(AlreadyFinished, d.addActionFinish)


    @withActionContext
    def test_addCallbacksRaisesAfterAddActionFinish(self):
        """
        After L{DeferredContext.addActionFinish} is called, additional calls to
        L{DeferredContext.addCallbacks} result in a L{AlreadyFinished}
        exception.
        """
        d = DeferredContext(Deferred())
        d.addActionFinish()
        self.assertRaises(AlreadyFinished, d.addCallbacks, lambda x: x,
                          lambda x: x)


    @withActionContext
    def test_addActionFinishResult(self):
        """
        L{DeferredContext.addActionFinish} returns the L{Deferred}.
        """
        d = Deferred()
        self.assertIs(d, DeferredContext(d).addActionFinish())


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



class RedirectLogsForTrialTests(TestCase):
    """
    Tests for L{redirectLogsForTrial}.
    """
    def assertDestinationAdded(self, programPath):
        """
        Assert that when running under the given program a new destination is
        added by L{redirectLogsForTrial}.

        @param programPath: A path to a program.
        @type programPath: L{str}
        """
        destination = redirectLogsForTrial(FakeSys([programPath], b""))
        # If this was not added as destination, removing it will raise an
        # exception:
        try:
            removeDestination(destination)
        except ValueError:
            self.fail("Destination was not added.")


    def test_withTrial(self):
        """
        When C{sys.argv[0]} is C{"trial"} a new destination is added by
        L{redirectLogsForTrial}.
        """
        self.assertDestinationAdded("trial")


    def test_withAbsoluteTrialPath(self):
        """
        When C{sys.argv[0]} is an absolute path ending with C{"trial"} a new
        destination is added by L{redirectLogsForTrial}.
        """
        self.assertDestinationAdded("/usr/bin/trial")


    def test_withRelativeTrialPath(self):
        """
        When C{sys.argv[0]} is a relative path ending with C{"trial"} a new
        destination is added by L{redirectLogsForTrial}.
        """
        self.assertDestinationAdded("./trial")


    def test_withoutTrialNoDestination(self):
        """
        When C{sys.argv[0]} is not C{"trial"} no destination is added by
        L{redirectLogsForTrial}.
        """
        originalDestinations = Logger._destinations._destinations[:]
        redirectLogsForTrial(FakeSys(["myprogram.py"], b""))
        self.assertEqual(Logger._destinations._destinations,
                         originalDestinations)


    def test_trialAsPathNoDestination(self):
        """
        When C{sys.argv[0]} has C{"trial"} as directory name but not program
        name no destination is added by L{redirectLogsForTrial}.
        """
        originalDestinations = Logger._destinations._destinations[:]
        redirectLogsForTrial(FakeSys(["./trial/myprogram.py"], b""))
        self.assertEqual(Logger._destinations._destinations,
                         originalDestinations)


    def test_withoutTrialResult(self):
        """
        When not running under I{trial} L{None} is returned.
        """
        self.assertIs(
            None, redirectLogsForTrial(FakeSys(["myprogram.py"], b"")))



    def redirectToLogPublisher(self):
        """
        Redirect Eliot logs to a Twisted log publisher.

        @return: L{list} of L{str} - the written, formatted Twisted log
            messages will eventually be added to it.
        """
        written = []
        publisher = LogPublisher()
        publisher.addObserver(lambda m: written.append(textFromEventDict(m)))
        destination = redirectLogsForTrial(FakeSys(["trial"], b""), publisher)
        self.addCleanup(removeDestination, destination)
        return written


    def redirectToList(self):
        """
        Redirect Eliot logs to a list.

        @return: L{list} that will have eventually have the written Eliot
            messages added to it.
        """
        written = []
        destination = written.append
        addDestination(destination)
        self.addCleanup(removeDestination, destination)
        return written


    def test_normalMessages(self):
        """
        Regular eliot messages are pretty-printed to the given L{LogPublisher}.
        """
        writtenToTwisted = self.redirectToLogPublisher()
        written = self.redirectToList()
        logger = Logger()
        Message.new(x=123, y=456).write(logger)
        self.assertEqual(writtenToTwisted,
                         ["ELIOT: %s" % (pformat(written[0]),)])


    def test_tracebackMessages(self):
        """
        Traceback eliot messages are written to the given L{LogPublisher} with
        the traceback formatted for easier reading.
        """
        writtenToTwisted = self.redirectToLogPublisher()
        written = self.redirectToList()
        logger = Logger()

        def raiser():
            raise RuntimeError("because")
        try:
            raiser()
        except Exception:
            expectedTraceback = traceback.format_exc()
            writeTraceback(logger, "some:system")

        lines = expectedTraceback.split("\n")
        # Remove source code lines:
        expectedTraceback = "\n".join(
            [l for l in lines if not l.startswith("    ")])

        self.assertEqual(writtenToTwisted,
                         ["ELIOT: %s" % (pformat(written[0]),),
                          "ELIOT Extracted Traceback:\n%s" % expectedTraceback])


    def test_defaults(self):
        """
        By default L{redirectLogsForTrial} looks at L{sys.argv} and
        L{twisted.python.log} for trial detection and log output.
        """
        self.assertEqual(inspect.getargspec(redirectLogsForTrial).defaults,
                         (sys, twlog))
