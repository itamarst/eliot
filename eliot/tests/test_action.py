"""
Tests for L{eliot._action}.
"""

from __future__ import unicode_literals

from unittest import TestCase, SkipTest
from threading import Thread

try:
    import twisted
    from twisted.internet.defer import Deferred
    from twisted.python.failure import Failure
except ImportError:
    twisted = None

from .._action import (
    Action, _ExecutionContext, currentAction, startTask, startAction,
    )
from .._output import MemoryLogger
from .._validation import ActionType, Field, _ActionSerializers
from ..testing import assertContainsFields
from .. import _action


class ExecutionContextTests(TestCase):
    """
    Tests for L{_ExecutionContext}.
    """
    def test_nothingPushed(self):
        """
        If no action has been pushed, L{_ExecutionContext.current} returns
        C{None}.
        """
        ctx = _ExecutionContext()
        self.assertIs(ctx.current(), None)


    def test_pushSingle(self):
        """
        L{_ExecutionContext.current} returns the action passed to
        L{_ExecutionContext.push} (assuming no pops).
        """
        ctx = _ExecutionContext()
        a = object()
        ctx.push(a)
        self.assertIs(ctx.current(), a)


    def test_pushMultiple(self):
        """
        L{_ExecutionContext.current} returns the action passed to the last
        call to L{_ExecutionContext.push} (assuming no pops).
        """
        ctx = _ExecutionContext()
        a = object()
        b = object()
        ctx.push(a)
        ctx.push(b)
        self.assertIs(ctx.current(), b)


    def test_multipleCurrent(self):
        """
        Multiple calls to L{_ExecutionContext.current} return the same result.
        """
        ctx = _ExecutionContext()
        a = object()
        ctx.push(a)
        ctx.current()
        self.assertIs(ctx.current(), a)


    def test_popSingle(self):
        """
        L{_ExecutionContext.pop} cancels a L{_ExecutionContext.push}, leading
        to an empty context.
        """
        ctx = _ExecutionContext()
        a = object()
        ctx.push(a)
        ctx.pop()
        self.assertIs(ctx.current(), None)


    def test_popMultiple(self):
        """
        L{_ExecutionContext.pop} cancels the last L{_ExecutionContext.push},
        resulting in current context being whatever was pushed before that.
        """
        ctx = _ExecutionContext()
        a = object()
        b = object()
        ctx.push(a)
        ctx.push(b)
        ctx.pop()
        self.assertIs(ctx.current(), a)


    def test_threadStart(self):
        """
        Each thread starts with an empty execution context.
        """
        ctx = _ExecutionContext()
        first = object()
        ctx.push(first)

        valuesInThread = []
        def inthread():
            valuesInThread.append(ctx.current())
        thread = Thread(target=inthread)
        thread.start()
        thread.join()
        self.assertEqual(valuesInThread, [None])


    def test_threadSafety(self):
        """
        Each thread gets its own execution context.
        """
        ctx = _ExecutionContext()
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


    def test_globalInstance(self):
        """
        A global L{_ExecutionContext} is exposed in the L{eliot._action}
        module.
        """
        self.assertIsInstance(_action._context, _ExecutionContext)
        self.assertEqual(_action.currentAction, _action._context.current)



class ActionTests(TestCase):
    """
    Tests for L{Action}.
    """
    def test_start(self):
        """
        L{Action._start} logs an C{action_status="started"} message.
        """
        logger = MemoryLogger()
        action = Action(logger, "unique", "/", "sys:thename")
        action._start({"key": "value"})
        assertContainsFields(self, logger.messages[0],
                             {"task_uuid": "unique",
                              "task_level": "/",
                              "action_counter": 0,
                              "action_type": "sys:thename",
                              "action_status": "started",
                              "key": "value"})


    def test_startMessageSerialization(self):
        """
        The start message logged by L{Action._start} is created with the
        appropriate start message L{eliot._validation._MessageSerializer}.
        """
        serializers = ActionType("sys:thename",
                                 [Field("key", lambda x: x, "")],
                                 [], [], "")._serializers
        class Logger(list):
            def write(self, msg, serializer):
                self.append(serializer)
        logger = Logger()
        action = Action(logger, "unique", "/", "sys:thename", serializers)
        action._start({"key": "value"})
        self.assertIs(logger[0], serializers.start)


    def test_child(self):
        """
        L{Action.child} returns a new L{Action} with the given logger, system
        and name, and a task_uuid taken from the parent L{Action}.
        """
        logger = MemoryLogger()
        action = Action(logger, "unique", "/", "sys:thename")
        logger2 = MemoryLogger()
        child = action.child(logger2, "newsystem:newname")
        self.assertIs(child._logger, logger2)
        self.assertEqual(child._identification,
                         {"task_uuid": "unique",
                          "task_level": "/1/",
                          "action_type": "newsystem:newname"})


    def test_childLevel(self):
        """
        Each call to L{Action.child} increments the new sub-level set on the
        child.
        """
        logger = MemoryLogger()
        action = Action(logger, "unique", "/", "sys:thename")
        child1 = action.child(logger, "newsystem:newname")
        child2 = action.child(logger, "newsystem:newname")
        child1_1 = child1.child(logger, "newsystem:other")
        self.assertEqual(child1._identification["task_level"], "/1/")
        self.assertEqual(child2._identification["task_level"], "/2/")
        self.assertEqual(child1_1._identification["task_level"], "/1/1/")


    def test_childSerializers(self):
        """
        L{Action.child} returns a new L{Action} with the serializers passed to
        it, rather than the parent's.
        """
        logger = MemoryLogger()
        serializers = object()
        action = Action(logger, "unique", "/", "sys:thename", serializers)
        childSerializers = object()
        child = action.child(logger, "newsystem:newname", childSerializers)
        self.assertIs(child._serializers, childSerializers)


    def test_run(self):
        """
        L{Action.run} runs the given function with given arguments, returning
        its result.
        """
        action = Action(None, "", "", "")
        def f(*args, **kwargs):
            return args, kwargs
        result = action.run(f, 1, 2, x=3)
        self.assertEqual(result, ((1, 2), {"x": 3}))


    def test_runContext(self):
        """
        L{Action.run} runs the given function with the action set as the
        current action.
        """
        result = []
        action = Action(None, "", "", "")
        action.run(lambda: result.append(currentAction()))
        self.assertEqual(result, [action])


    def test_runContextUnsetOnReturn(self):
        """
        L{Action.run} unsets the action once the given function returns.
        """
        action = Action(None, "", "", "")
        action.run(lambda: None)
        self.assertIs(currentAction(), None)


    def test_runContextUnsetOnRaise(self):
        """
        L{Action.run} unsets the action once the given function raises an
        exception.
        """
        action = Action(None, "", "", "")
        self.assertRaises(ZeroDivisionError, action.run, lambda: 1/0)
        self.assertIs(currentAction(), None)


    def test_runCallback(self):
        """
        L{Action.runCallback} calls L{Action.run} with the first and second
        arguments swapped.
        """
        ran = []
        class TestAction(Action):
            def run(self, *args, **kwargs):
                ran.append((args, kwargs))
                return Action.run(self, *args, **kwargs)

        def f(result, extra, extra2):
            pass

        action = TestAction(None, "", "", "")
        action.runCallback("hi", f, 2, extra2=3)
        self.assertEqual(ran, [((f, "hi", 2), {"extra2": 3})])



    def test_runCallbackResult(self):
        """
        L{Action.runCallback} returns the result of the function it runs.
        """
        def f(result, extra):
            return result + extra

        action = Action(None, "", "", "")
        result = action.runCallback("hi", f, "bye")
        self.assertEqual(result, "hibye")


    def test_withSetsContext(self):
        """
        L{Action.__enter__} sets the action as the current action.
        """
        action = Action(MemoryLogger(), "", "", "")
        with action:
            self.assertIs(currentAction(), action)


    def test_withUnsetOnReturn(self):
        """
        L{Action.__exit__} unsets the action on successful block finish.
        """
        action = Action(MemoryLogger(), "", "", "")
        with action:
            pass
        self.assertIs(currentAction(), None)


    def test_withUnsetOnRaise(self):
        """
        L{Action.__exit__} unsets the action if the block raises an exception.
        """
        action = Action(MemoryLogger(), "", "", "")
        try:
            with action:
                1/0
        except ZeroDivisionError:
            pass
        else:
            self.fail("no exception")
        self.assertIs(currentAction(), None)


    def test_finish(self):
        """
        L{Action.finish} with no exception logs an C{action_status="succeeded"}
        message.
        """
        logger = MemoryLogger()
        action = Action(logger, "unique", "/", "sys:thename")
        action.finish()
        assertContainsFields(self, logger.messages[0],
                             {"task_uuid": "unique",
                              "task_level": "/",
                              "action_type": "sys:thename",
                              "action_status": "succeeded"})


    def test_successfulFinishSerializer(self):
        """
        L{Action.finish} with no exception passes the success
        L{eliot._validation._MessageSerializer} to the message it creates.
        """
        serializers = ActionType("sys:thename",
                                 [],
                                 [Field("key", lambda x: x, "")],
                                 [], "")._serializers
        class Logger(list):
            def write(self, msg, serializer):
                self.append(serializer)
        logger = Logger()
        action = Action(logger, "unique", "/", "sys:thename", serializers)
        action.finish()
        self.assertIs(logger[0], serializers.success)


    def test_failureFinishSerializer(self):
        """
        L{Action.finish} with an exception passes the failure
        L{eliot._validation._MessageSerializer} to the message it creates.
        """
        serializers = ActionType("sys:thename", [], [],
                                 [Field("key", lambda x: x, "")],
                                 "")._serializers
        class Logger(list):
            def write(self, msg, serializer):
                self.append(serializer)
        logger = Logger()
        action = Action(logger, "unique", "/", "sys:thename", serializers)
        action.finish(Exception())
        self.assertIs(logger[0], serializers.failure)


    def test_startFieldsNotInFinish(self):
        """
        L{Action.finish} logs a message without the fields from
        L{Action._start}.
        """
        logger = MemoryLogger()
        action = Action(logger, "unique", "/", "sys:thename")
        action._start({"key": "value"})
        action.finish()
        self.assertNotIn("key", logger.messages[1])


    def test_finishWithBadException(self):
        """
        L{Action.finish} still logs a message if the given exception raises
        another exception when called with C{unicode()}.
        """
        logger = MemoryLogger()
        action = Action(logger, "unique", "/", "sys:thename")
        class BadException(Exception):
            def __str__(self):
                raise TypeError()
        action.finish(BadException())
        self.assertEqual(logger.messages[0]["reason"],
                         "eliot: unknown, unicode() raised exception")


    def test_withLogsSuccessfulFinishMessage(self):
        """
        L{Action.__exit__} logs an action finish message on a successful block
        finish.
        """
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        with action:
            pass
        # Start message is only created if we use the action()/task() utility
        # functions, the intended public APIs.
        self.assertEqual(len(logger.messages), 1)
        assertContainsFields(self, logger.messages[0],
                             {"task_uuid": "uuid",
                              "task_level": "/1/",
                              "action_type": "sys:me",
                              "action_status": "succeeded"})


    def test_withLogsExceptionMessage(self):
        """
        L{Action.__exit__} logs an action finish message on an exception
        raised from the block.
        """
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        exception = RuntimeError("because")

        try:
            with action:
                raise exception
        except RuntimeError:
            pass
        else:
            self.fail("no exception")

        self.assertEqual(len(logger.messages), 1)
        assertContainsFields(self, logger.messages[0],
                             {"task_uuid": "uuid",
                              "task_level": "/1/",
                              "action_type": "sys:me",
                              "action_status": "failed",
                              "reason": "because",
                              "exception": "exceptions.RuntimeError"})


    def test_withReturnValue(self):
        """
        L{Action.__enter__} returns the action itself.
        """
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        with action as act:
            self.assertIs(action, act)


    def test_addSuccessFields(self):
        """
        On a successful finish, L{Action.__exit__} adds fields from
        L{Action.addSuccessFields} to the result message.
        """
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        with action as act:
            act.addSuccessFields(x=1, y=2)
            act.addSuccessFields(z=3)
        assertContainsFields(self, logger.messages[0],
                             {"x": 1, "y": 2, "z": 3})


    def test_addSuccessFieldsIgnoresFailure(self):
        """
        On a successful finish, L{Action.__exit__} ignores fields from
        L{Action.addFailureFields}.
        """
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        with action as act:
            act.addFailureFields(z=3)
        self.assertNotIn("z", logger.messages[0])


    def test_addFailureFields(self):
        """
        On an failed finish, L{Action.__exit__} adds fields from
        L{Action.addFailureFields} to the result message.
        """
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        try:
            with action as act:
                act.addFailureFields(x=1, y=2)
                act.addFailureFields(z=3)
                raise RuntimeError()
        except RuntimeError:
            pass
        else:
            self.fail("No exception")
        assertContainsFields(self, logger.messages[0],
                             {"x": 1, "y": 2, "z": 3})


    def test_addFailureFieldsIgnoresSuccess(self):
        """
        On a successful finish, L{Action.__exit__} ignores fields from
        L{Action.addFailureFields}.
        """
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        try:
            with action as act:
                act.addSuccessFields(z=3)
                raise RuntimeError()
        except RuntimeError:
            pass
        else:
            self.fail("No exception")
        self.assertNotIn("z", logger.messages[0])


    def test_incrementMessageCounter(self):
        """
        Each call to L{Action._incrementMessageCounter} increments a counter.
        """
        action = Action(MemoryLogger(), "uuid", "/1/", "sys:me")
        self.assertEqual([action._incrementMessageCounter() for i in range(5)],
                         range(5))


    def test_multipleFinishCalls(self):
        """
        If L{Action.finish} is called, subsequent calls to L{Action.finish} have
        no effect.
        """
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        with action as act:
            act.finish()
            act.finish(Exception())
            act.finish()
        # Only initial finish message is logged:
        self.assertEqual(len(logger.messages), 1)



class TwistedActionTests(TestCase):
    """
    Tests for Twisted-specific L{Action} APIs.
    """
    def setUp(self):
        if twisted is None:
            raise SkipTest("Twisted not available")


    def test_finishAfterNoImmediateLogging(self):
        """
        L{Action.finishAfter} does not log anything if the L{Deferred} hasn't
        fired yet.
        """
        d = Deferred()
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        action.finishAfter(d)
        self.assertFalse(logger.messages)


    def test_finishAfterSuccess(self):
        """
        When the L{Deferred} passed to L{Action.finishAfter} fires
        successfully, a finish message is logged with any success bindings
        added.
        """
        d = Deferred()
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        action.addSuccessFields(x=2)
        action.finishAfter(d)
        d.callback("result")
        assertContainsFields(self, logger.messages[0],
                             {"task_uuid": "uuid",
                              "task_level": "/1/",
                              "action_type": "sys:me",
                              "action_status": "succeeded",
                              "x": 2})


    def test_finishAfterSuccessPassThrough(self):
        """
        L{Action.finishAfter} passes through a successful result unchanged.
        """
        d = Deferred()
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        action.finishAfter(d)
        d.callback("result")
        result = []
        d.addCallback(result.append)
        self.assertEqual(result, ["result"])


    def test_finishAfterFailure(self):
        """
        When the L{Deferred} passed to L{Action.finishAfter} fires
        with an exception, a finish message is logged with any failure bindings
        added.
        """
        d = Deferred()
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        action.addFailureFields(x=2)
        action.finishAfter(d)
        exception = RuntimeError("because")
        d.errback(exception)
        assertContainsFields(self, logger.messages[0],
                             {"task_uuid": "uuid",
                              "task_level": "/1/",
                              "action_type": "sys:me",
                              "action_status": "failed",
                              "x": 2,
                              "reason": "because",
                              "exception": "exceptions.RuntimeError"})
        d.addErrback(lambda _: None) # don't let Failure go to Twisted logs


    def test_finishAfterFailurePassThrough(self):
        """
        L{Action.finishAfter} passes through a failed result unchanged.
        """
        d = Deferred()
        logger = MemoryLogger()
        action = Action(logger, "uuid", "/1/", "sys:me")
        action.finishAfter(d)
        failure = Failure(RuntimeError())
        d.errback(failure)
        result = []
        d.addErrback(result.append)
        self.assertEqual(result, [failure])



class StartActionAndTaskTests(TestCase):
    """
    Tests for L{startAction} and L{startTask}.
    """
    def test_startTaskNewAction(self):
        """
        L{startTask} creates a new top-level L{Action}.
        """
        logger = MemoryLogger()
        action = startTask(logger, "sys:do")
        self.assertIsInstance(action, Action)
        self.assertEqual(action._identification["task_level"], "/")


    def test_startTaskSerializers(self):
        """
        If serializers are passed to L{startTask} they are attached to the
        resulting L{Action}.
        """
        logger = MemoryLogger()
        serializers = _ActionSerializers(None, None, None)
        action = startTask(logger, "sys:do", serializers)
        self.assertIs(action._serializers, serializers)


    def test_startActionSerializers(self):
        """
        If serializers are passed to L{startAction} they are attached to the
        resulting L{Action}.
        """
        logger = MemoryLogger()
        serializers = _ActionSerializers(None, None, None)
        action = startAction(logger, "sys:do", serializers)
        self.assertIs(action._serializers, serializers)


    def test_startTaskNewUUID(self):
        """
        L{startTask} creates an L{Action} with its own C{task_uuid}.
        """
        logger = MemoryLogger()
        action = startTask(logger, "sys:do")
        action2 = startTask(logger, "sys:do")
        self.assertNotEqual(action._identification["task_uuid"],
                            action2._identification["task_uuid"])


    def test_startTaskLogsStart(self):
        """
        L{startTask} logs a start message for the newly created L{Action}.
        """
        logger = MemoryLogger()
        action = startTask(logger, "sys:do", key="value")
        assertContainsFields(self, logger.messages[0],
                             {"task_uuid": action._identification["task_uuid"],
                              "task_level": "/",
                              "action_type": "sys:do",
                              "action_status": "started",
                              "key": "value"})


    def test_startActionNoParent(self):
        """
        L{startAction} when C{currentAction()} is C{None} creates a top-level
        L{Action}.
        """
        logger = MemoryLogger()
        action = startAction(logger, "sys:do")
        self.assertIsInstance(action, Action)
        self.assertEqual(action._identification["task_level"], "/")


    def test_startActionNoParentLogStart(self):
        """
        L{startAction} when C{currentAction()} is C{None} logs a start
        message.
        """
        logger = MemoryLogger()
        action = startAction(logger, "sys:do", key="value")
        assertContainsFields(self, logger.messages[0],
                             {"task_uuid": action._identification["task_uuid"],
                              "task_level": "/",
                              "action_type": "sys:do",
                              "action_status": "started",
                              "key": "value"})


    def test_startActionWithParent(self):
        """
        L{startAction} uses the C{currentAction()} as parent for a new
        L{Action}.
        """
        logger = MemoryLogger()
        parent = Action(logger, "uuid", "/2/", "other:thing")
        with parent:
            action = startAction(logger, "sys:do")
            self.assertIsInstance(action, Action)
            self.assertEqual(action._identification["task_uuid"], "uuid")
            self.assertEqual(action._identification["task_level"], "/2/1/")


    def test_startActionWithParentLogStart(self):
        """
        L{startAction} when C{currentAction()} is an L{Action} logs a start
        message.
        """
        logger = MemoryLogger()
        parent = Action(logger, "uuid", "/", "other:thing")
        with parent:
            startAction(logger, "sys:do", key="value")
            assertContainsFields(self, logger.messages[0],
                                 {"task_uuid": "uuid",
                                  "task_level": "/1/",
                                  "action_type": "sys:do",
                                  "action_status": "started",
                                  "key": "value"})
