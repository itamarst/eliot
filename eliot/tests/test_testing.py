"""
Tests for L{eliot.testing}.
"""

from __future__ import unicode_literals

from unittest import SkipTest, TestResult, TestCase

from ..testing import (
    issuperset, assertContainsFields, LoggedAction, LoggedMessage,
    validateLogging, UnflushedTracebacks, assertHasMessage, assertHasAction,
    validate_logging,
    )
from .._output import MemoryLogger
from .._action import startAction
from .._message import Message
from .._validation import ActionType, MessageType, ValidationError, Field
from .._traceback import writeTraceback


class IsSuperSetTests(TestCase):
    """
    Tests for L{issuperset}.
    """
    def test_equal(self):
        """
        Equal dictionaries are supersets of each other.
        """
        a = {"a": 1}
        b = a.copy()
        self.assertTrue(issuperset(a, b))


    def test_additionalIsSuperSet(self):
        """
        If C{A} is C{B} plus some extra entries, C{A} is superset of C{B}.
        """
        a = {"a": 1, "b": 2, "c": 3}
        b = {"a": 1, "c": 3}
        self.assertTrue(issuperset(a, b))


    def test_missingIsNotSuperSet(self):
        """
        If C{A} is C{B} minus some entries, C{A} is not a superset of C{B}.
        """
        a = {"a": 1, "c": 3}
        b = {"a": 1, "b": 2, "c": 3}
        self.assertFalse(issuperset(a, b))



class LoggedActionTests(TestCase):
    """
    Tests for L{LoggedAction}.
    """
    def test_values(self):
        """
        The values given to the L{LoggedAction} constructor are stored on it.
        """
        d1 = {'x': 1}
        d2 = {'y': 2}
        root = LoggedAction(d1, d2, [])
        self.assertEqual((root.startMessage, root.endMessage), (d1, d2))


    def fromMessagesIndex(self, messages, index):
        """
        Call L{LoggedAction.fromMessages} using action specified by index in
        a list of message dictionaries.

        @param messages: A C{list} of message dictionaries.

        @param index: Index to the logger's messages.

        @return: Result of L{LoggedAction.fromMessages}.
        """
        uuid = messages[index]["task_uuid"]
        level = messages[index]["task_level"]
        return LoggedAction.fromMessages(uuid, level, messages)


    def test_fromMessagesCreatesLoggedAction(self):
        """
        L{LoggedAction.fromMessages} returns a L{LoggedAction}.
        """
        logger = MemoryLogger()
        with startAction(logger, "test"):
            pass
        logged = self.fromMessagesIndex(logger.messages, 0)
        self.assertIsInstance(logged, LoggedAction)


    def test_fromMessagesStartAndSuccessfulFinish(self):
        """
        L{LoggedAction.fromMessages} finds the start and successful finish
        messages of an action and stores them in the result.
        """
        logger = MemoryLogger()
        Message.new(x=1).write(logger)
        with startAction(logger, "test"):
            Message.new(x=1).write(logger)
        # Now we should have x message, start action message, another x message
        # and finally finish message.
        logged = self.fromMessagesIndex(logger.messages, 1)
        self.assertEqual((logged.startMessage, logged.endMessage),
                         (logger.messages[1], logger.messages[3]))


    def test_fromMessagesStartAndErrorFinish(self):
        """
        L{LoggedAction.fromMessages} finds the start and successful finish
        messages of an action and stores them in the result.
        """
        logger = MemoryLogger()
        try:
            with startAction(logger, "test"):
                raise KeyError()
        except KeyError:
            pass
        logged = self.fromMessagesIndex(logger.messages, 0)
        self.assertEqual((logged.startMessage, logged.endMessage),
                         (logger.messages[0], logger.messages[1]))


    def test_fromMessagesStartNotFound(self):
        """
        L{LoggedAction.fromMessages} raises a L{ValueError} if a start message
        is not found.
        """
        logger = MemoryLogger()
        with startAction(logger, "test"):
            pass
        self.assertRaises(ValueError,
                          self.fromMessagesIndex, logger.messages[1:], 0)


    def test_fromMessagesFinishNotFound(self):
        """
        L{LoggedAction.fromMessages} raises a L{ValueError} if a finish message
        is not found.
        """
        logger = MemoryLogger()
        with startAction(logger, "test"):
            pass
        self.assertRaises(ValueError,
                          self.fromMessagesIndex, logger.messages[:1], 0)


    def test_fromMessagesAddsChildMessages(self):
        """
        L{LoggedAction.fromMessages} adds direct child messages to the
        constructed L{LoggedAction}.
        """
        logger = MemoryLogger()
        # index 0:
        Message.new(x=1).write(logger)
        # index 1 - start action
        with startAction(logger, "test"):
            # index 2
            Message.new(x=2).write(logger)
            # index 3
            Message.new(x=3).write(logger)
        # index 4 - end action
        # index 5
        Message.new(x=4).write(logger)
        logged = self.fromMessagesIndex(logger.messages, 1)

        expectedChildren = [LoggedMessage(logger.messages[2]),
                            LoggedMessage(logger.messages[3])]
        self.assertEqual(logged.children, expectedChildren)


    def test_fromMessagesAddsChildActions(self):
        """
        L{LoggedAction.fromMessages} recursively adds direct child actions to
        the constructed L{LoggedAction}.
        """
        logger = MemoryLogger()
        # index 0
        with startAction(logger, "test"):
            # index 1:
            with startAction(logger, "test"):
                # index 2
                Message.new(x=2).write(logger)
            # index 3 - end action
        # index 4 - end action
        logged = self.fromMessagesIndex(logger.messages, 0)

        self.assertEqual(logged.children[0],
                         self.fromMessagesIndex(logger.messages, 1))


    def test_ofType(self):
        """
        L{LoggedAction.ofType} returns a list of L{LoggedAction} created by the
        specified L{ActionType}.
        """
        ACTION = ActionType("myaction", [], [], "An action!")
        logger = MemoryLogger()
        # index 0
        with startAction(logger, "test"):
            # index 1:
            with ACTION(logger):
                # index 2
                Message.new(x=2).write(logger)
            # index 3 - end action
        # index 4 - end action
        # index 5
        with ACTION(logger):
            pass
        # index 6 - end action
        logged = LoggedAction.ofType(logger.messages, ACTION)
        self.assertEqual(logged, [self.fromMessagesIndex(logger.messages, 1),
                                  self.fromMessagesIndex(logger.messages, 5)])


    def test_ofTypeNotFound(self):
        """
        L{LoggedAction.ofType} returns an empty list if actions of the given
        type cannot be found.
        """
        ACTION = ActionType("myaction", [], [], "An action!")
        logger = MemoryLogger()
        self.assertEqual(LoggedAction.ofType(logger.messages, ACTION), [])


    def test_descendants(self):
        """
        L{LoggedAction.descendants} returns all descendants of the
        L{LoggedAction}.
        """
        ACTION = ActionType("myaction", [], [], "An action!")
        logger = MemoryLogger()
        # index 0
        with ACTION(logger):
            # index 1:
            with startAction(logger, "test"):
                # index 2
                Message.new(x=2).write(logger)
            # index 3 - end action
            # index 4
            Message.new(x=2).write(logger)
        # index 5 - end action

        loggedAction = LoggedAction.ofType(logger.messages, ACTION)[0]
        self.assertEqual(list(loggedAction.descendants()),
                         [self.fromMessagesIndex(logger.messages, 1),
                          LoggedMessage(logger.messages[2]),
                          LoggedMessage(logger.messages[4])])


    def test_succeeded(self):
        """
        If the action succeeded, L{LoggedAction.succeeded} will be true.
        """
        logger = MemoryLogger()
        with startAction(logger, "test"):
            pass
        logged = self.fromMessagesIndex(logger.messages, 0)
        self.assertTrue(logged.succeeded)


    def test_notSucceeded(self):
        """
        If the action failed, L{LoggedAction.succeeded} will be false.
        """
        logger = MemoryLogger()
        try:
            with startAction(logger, "test"):
                raise KeyError()
        except KeyError:
            pass
        logged = self.fromMessagesIndex(logger.messages, 0)
        self.assertFalse(logged.succeeded)



class LoggedMessageTest(TestCase):
    """
    Tests for L{LoggedMessage}.
    """
    def test_values(self):
        """
        The values given to the L{LoggedMessage} constructor are stored on it.
        """
        message = {'x': 1}
        logged = LoggedMessage(message)
        self.assertEqual(logged.message, message)


    def test_ofType(self):
        """
        L{LoggedMessage.ofType} returns a list of L{LoggedMessage} created by the
        specified L{MessageType}.
        """
        MESSAGE = MessageType("mymessage", [], "A message!")
        logger = MemoryLogger()
        # index 0
        MESSAGE().write(logger)
        # index 1
        Message.new(x=2).write(logger)
        # index 2
        MESSAGE().write(logger)
        logged = LoggedMessage.ofType(logger.messages, MESSAGE)
        self.assertEqual(logged, [LoggedMessage(logger.messages[0]),
                                  LoggedMessage(logger.messages[2])])


    def test_ofTypeNotFound(self):
        """
        L{LoggedMessage.ofType} returns an empty list if messages of the given
        type cannot be found.
        """
        MESSAGE = MessageType("mymessage", [], "A message!")
        logger = MemoryLogger()
        self.assertEqual(LoggedMessage.ofType(logger.messages, MESSAGE), [])



class AssertContainsFields(TestCase):
    """
    Tests for L{assertContainsFields}.
    """
    class ContainsTest(TestCase):
        """
        A test case that uses L{assertContainsFields}.
        """
        def __init__(self, message, expectedFields):
            TestCase.__init__(self)
            self.message = message
            self.expectedFields = expectedFields

        def runTest(self):
            assertContainsFields(self, self.message, self.expectedFields)


    def test_equal(self):
        """
        Equal dictionaries contain each other.
        """
        message = {"a": 1}
        expected = message.copy()
        test = self.ContainsTest(message, expected)
        # No exception raised:
        test.debug()


    def test_additionalIsSuperSet(self):
        """
        If C{A} is C{B} plus some extra entries, C{A} contains the fields in
        C{B}.
        """
        message = {"a": 1, "b": 2, "c": 3}
        expected = {"a": 1, "c": 3}
        test = self.ContainsTest(message, expected)
        # No exception raised:
        test.debug()


    def test_missingFields(self):
        """
        If C{A} is C{B} minus some entries, C{A} does not contain the fields in
        C{B}.
        """
        message = {"a": 1, "c": 3}
        expected = {"a": 1, "b": 2, "c": 3}
        test = self.ContainsTest(message, expected)
        self.assertRaises(AssertionError, test.debug)


    def test_differentValues(self):
        """
        If C{A} has a different value for a specific field than C{B}, C{A} does
        not contain the fields in C{B}.
        """
        message = {"a": 1, "c": 3}
        expected = {"a": 1, "c": 2}
        test = self.ContainsTest(message, expected)
        self.assertRaises(AssertionError, test.debug)



class ValidateLoggingTests(TestCase):
    """
    Tests for L{validateLogging}.
    """
    def test_decoratedFunctionCalledWithMemoryLogger(self):
        """
        The underlying function decorated with L{validateLogging} is called with
        a L{MemoryLogger} instance in addition to any other arguments if the
        wrapper is called.
        """
        result = []
        class MyTest(TestCase):
            @validateLogging(None)
            def test_foo(this, logger):
                result.append((this, logger.__class__))

        theTest = MyTest("test_foo")
        theTest.test_foo()
        self.assertEqual(result, [(theTest, MemoryLogger)])


    def test_newMemoryLogger(self):
        """
        The underlying function decorated with L{validateLogging} is called with
        a new L{MemoryLogger} every time the wrapper is called.
        """
        result = []
        class MyTest(TestCase):
            @validateLogging(None)
            def test_foo(this, logger):
                result.append(logger)

        theTest = MyTest("test_foo")
        theTest.test_foo()
        theTest.test_foo()
        self.assertIsNot(result[0], result[1])


    def test_returns(self):
        """
        The result of the underlying function is returned by wrapper when called.
        """
        class MyTest(TestCase):
            @validateLogging(None)
            def test_foo(self, logger):
                return 123
        self.assertEqual(MyTest("test_foo").test_foo(), 123)


    def test_raises(self):
        """
        The exception raised by the underlying function is passed through by the
        wrapper when called.
        """
        exc = Exception()
        class MyTest(TestCase):
            @validateLogging(None)
            def test_foo(self, logger):
                raise exc

        raised = None
        try:
            MyTest("test_foo").test_foo()
        except Exception as e:
            raised = e
        self.assertIs(exc, raised)


    def test_name(self):
        """
        The wrapper has the same name as the wrapped function.
        """
        class MyTest(TestCase):
            @validateLogging(None)
            def test_foo(self, logger):
                pass
        self.assertEqual(MyTest.test_foo.__name__, "test_foo")


    def test_addCleanupValidate(self):
        """
        When a test method is decorated with L{validateLogging} it has
        L{MemoryLogger.validate} registered as a test cleanup.
        """
        MESSAGE = MessageType("mymessage", [], "A message")

        class MyTest(TestCase):
            @validateLogging(None)
            def runTest(self, logger):
                self.logger = logger
                logger.write({"message_type": "wrongmessage"},
                             MESSAGE._serializer)
        test = MyTest()
        self.assertRaises(ValidationError, test.debug)
        self.assertEqual(list(test.logger.messages[0].keys()), ["message_type"])


    def test_addCleanupTracebacks(self):
        """
        When a test method is decorated with L{validateLogging} it has has a
        check unflushed tracebacks in the L{MemoryLogger} registered as a
        test cleanup.
        """
        class MyTest(TestCase):
            @validateLogging(None)
            def runTest(self, logger):
                try:
                    1 / 0
                except ZeroDivisionError:
                    writeTraceback(logger)
        test = MyTest()
        self.assertRaises(UnflushedTracebacks, test.debug)


    def test_assertion(self):
        """
        If a callable is passed to L{validateLogging}, it is called with the
        L{TestCase} instance and the L{MemoryLogger} passed to the test
        method.
        """
        result = []

        class MyTest(TestCase):
            def assertLogging(self, logger):
                result.append((self, logger))

            @validateLogging(assertLogging)
            def runTest(self, logger):
                self.logger = logger

        test = MyTest()
        test.run()
        self.assertEqual(result, [(test, test.logger)])


    def test_assertionArguments(self):
        """
        If a callable together with additional arguments and keyword arguments are
        passed to L{validateLogging}, the callable is called with the additional
        args and kwargs.
        """
        result = []

        class MyTest(TestCase):
            def assertLogging(self, logger, x, y):
                result.append((self, logger, x, y))

            @validateLogging(assertLogging, 1, y=2)
            def runTest(self, logger):
                self.logger = logger

        test = MyTest()
        test.run()
        self.assertEqual(result, [(test, test.logger, 1, 2)])


    def test_assertionAfterTest(self):
        """
        If a callable is passed to L{validateLogging}, it is called with the
        after the main test code has run, allowing it to make assertions
        about log messages from the test.
        """
        class MyTest(TestCase):
            def assertLogging(self, logger):
                self.result.append(2)

            @validateLogging(assertLogging)
            def runTest(self, logger):
                self.result = [1]

        test = MyTest()
        test.run()
        self.assertEqual(test.result, [1, 2])


    def test_assertionBeforeTracebackCleanup(self):
        """
        If a callable is passed to L{validateLogging}, it is called with the
        before the check for unflushed tracebacks, allowing it to flush
        traceback log messages.
        """
        class MyTest(TestCase):
            def assertLogging(self, logger):
                logger.flushTracebacks(ZeroDivisionError)
                self.flushed = True

            @validateLogging(assertLogging)
            def runTest(self, logger):
                self.flushed = False
                try:
                    1 / 0
                except ZeroDivisionError:
                    writeTraceback(logger)
        test = MyTest()
        test.debug()
        self.assertTrue(test.flushed)


    def test_validationNotRunForSkip(self):
        """
        If the decorated test raises L{SkipTest} then the logging validation is
        also skipped.
        """
        class MyTest(TestCase):
            recorded = False

            def record(self, logger):
                self.recorded = True

            @validateLogging(record)
            def runTest(self, logger):
                raise SkipTest("Do not run this test.")

        test = MyTest()
        result = TestResult()
        test.run(result)

        # Verify that the validation function did not run and that the test was
        # nevertheless marked as a skip with the correct reason.
        self.assertEqual(
            (test.recorded, result.skipped, result.errors, result.failures),
            (False, [(test, "Do not run this test.")], [], [])
        )


    def test_unflushedTracebacksDontFailForSkip(self):
        """
        If the decorated test raises L{SkipTest} then the unflushed traceback
        checking normally implied by L{validateLogging} is also skipped.
        """
        class MyTest(TestCase):

            @validateLogging(lambda self, logger: None)
            def runTest(self, logger):
                try:
                    1 / 0
                except:
                    writeTraceback(logger)
                raise SkipTest("Do not run this test.")

        test = MyTest()
        result = TestResult()
        test.run(result)

        # Verify that there was only a skip, no additional errors or failures
        # reported.
        self.assertEqual(
            (1, [], []),
            (len(result.skipped), result.errors, result.failures)
        )



MESSAGE1 = MessageType("message1", [Field.forTypes("x", [int], "A number")],
                       "A message for testing.")
MESSAGE2 = MessageType("message2", [], "A message for testing.")


class AssertHasMessageTests(TestCase):
    """
    Tests for L{assertHasMessage}.
    """
    class UnitTest(TestCase):
        """
        Test case that can be instantiated.
        """
        def runTest(self):
            pass


    def test_failIfNoMessagesOfType(self):
        """
        L{assertHasMessage} raises L{AssertionError} if the given L{MemoryLogger}
        has no messages of the given L{MessageType}.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        MESSAGE1(x=123).write(logger)
        self.assertRaises(AssertionError,
                          assertHasMessage, test, logger, MESSAGE2)


    def test_returnsIfMessagesOfType(self):
        """
        L{assertHasMessage} returns the first message of the given L{MessageType}.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        MESSAGE1(x=123).write(logger)
        self.assertEqual(assertHasMessage(test, logger, MESSAGE1),
                         LoggedMessage.ofType(logger.messages, MESSAGE1)[0])


    def test_failIfNotSubset(self):
        """
        L{assertHasMessage} raises L{AssertionError} if the found message doesn't
        contain the given fields.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        MESSAGE1(x=123).write(logger)
        self.assertRaises(AssertionError,
                          assertHasMessage, test, logger, MESSAGE1, {"x": 24})


    def test_returnsIfSubset(self):
        """
        L{assertHasMessage} returns the first message of the given L{MessageType} if
        it contains the given fields.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        MESSAGE1(x=123).write(logger)
        self.assertEqual(assertHasMessage(test, logger, MESSAGE1, {"x": 123}),
                         LoggedMessage.ofType(logger.messages, MESSAGE1)[0])


ACTION1 = ActionType("action1", [Field.forTypes("x", [int], "A number")],
                     [Field.forTypes("result", [int], "A number")],
                     "A action for testing.")
ACTION2 = ActionType("action2", [], [], "A action for testing.")


class AssertHasActionTests(TestCase):
    """
    Tests for L{assertHasAction}.
    """
    class UnitTest(TestCase):
        """
        Test case that can be instantiated.
        """
        def runTest(self):
            pass


    def test_failIfNoActionsOfType(self):
        """
        L{assertHasAction} raises L{AssertionError} if the given L{MemoryLogger}
        has no actions of the given L{ActionType}.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        with ACTION1(logger, x=123): pass
        self.assertRaises(AssertionError,
                          assertHasAction, test, logger, ACTION2, True)


    def test_failIfWrongSuccessStatus(self):
        """
        L{assertHasAction} raises L{AssertionError} if the given success status does
        not match that of the found actions.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        with ACTION1(logger, x=123): pass
        try:
            with ACTION2(logger):
                1/0
        except ZeroDivisionError:
            pass
        self.assertRaises(AssertionError,
                          assertHasAction, test, logger, ACTION1, False)
        self.assertRaises(AssertionError,
                          assertHasAction, test, logger, ACTION2, True)


    def test_returnsIfMessagesOfType(self):
        """
        A successful L{assertHasAction} returns the first message of the given
        L{ActionType}.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        with ACTION1(logger, x=123): pass
        self.assertEqual(assertHasAction(test, logger, ACTION1, True),
                         LoggedAction.ofType(logger.messages, ACTION1)[0])


    def test_failIfNotStartSubset(self):
        """
        L{assertHasAction} raises L{AssertionError} if the found action doesn't
        contain the given start fields.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        with ACTION1(logger, x=123): pass
        self.assertRaises(AssertionError,
                          assertHasAction, test, logger, ACTION1, True, {"x": 24})


    def test_failIfNotEndSubset(self):
        """
        L{assertHasAction} raises L{AssertionError} if the found action doesn't
        contain the given end fields.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        with ACTION1(logger, x=123) as act: act.addSuccessFields(result=5)
        self.assertRaises(AssertionError,
                          assertHasAction, test, logger, ACTION1, True,
                          startFields={"x": 123}, endFields={"result": 24})


    def test_returns(self):
        """
        A successful L{assertHasAction} returns the first message of the given
        L{ActionType} after doing all validation.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        with ACTION1(logger, x=123) as act: act.addSuccessFields(result=5)
        self.assertEqual(
            assertHasAction(test, logger, ACTION1, True,
                            {"x": 123}, {"result": 5}),
            LoggedAction.ofType(logger.messages, ACTION1)[0])



class PEP8Tests(TestCase):
    """
    Tests for PEP 8 method compatibility.
    """
    def test_LoggedAction_from_messages(self):
        """
        L{LoggedAction.from_messages} is the same as
        L{LoggedAction.fromMessages}.
        """
        self.assertEqual(LoggedAction.from_messages, LoggedAction.fromMessages)


    def test_LoggedAction_of_type(self):
        """
        L{LoggedAction.of_type} is the same as
        L{LoggedAction.ofType}.
        """
        self.assertEqual(LoggedAction.of_type, LoggedAction.ofType)


    def test_LoggedAction_end_message(self):
        """
        L{LoggedAction.end_message} is the same as L{LoggedAction.endMessage}.
        """
        action = LoggedAction({1: 2}, {3: 4}, [])
        self.assertEqual(action.end_message, action.endMessage)


    def test_LoggedAction_start_message(self):
        """
        L{LoggedAction.start_message} is the same as
        L{LoggedAction.startMessage}.
        """
        action = LoggedAction({1: 2}, {3: 4}, [])
        self.assertEqual(action.start_message, action.startMessage)


    def test_LoggedMessage_of_type(self):
        """
        L{LoggedMessage.of_type} is the same as
        L{LoggedMessage.ofType}.
        """
        self.assertEqual(LoggedMessage.of_type, LoggedMessage.ofType)


    def test_validate_logging(self):
        """
        L{validate_logging} is the same as L{validateLogging}.
        """
        self.assertEqual(validate_logging, validateLogging)


