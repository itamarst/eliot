"""
Tests for L{eliot.testing}.
"""


from unittest import SkipTest, TestResult, TestCase, skipUnless

try:
    import numpy as np
except ImportError:
    np = None

from ..testing import (
    issuperset,
    assertContainsFields,
    LoggedAction,
    LoggedMessage,
    validateLogging,
    UnflushedTracebacks,
    assertHasMessage,
    assertHasAction,
    validate_logging,
    capture_logging,
    swap_logger,
    check_for_errors,
)
from .._output import MemoryLogger
from .._action import start_action
from .._message import Message
from .._validation import ActionType, MessageType, ValidationError, Field
from .._traceback import write_traceback
from .. import add_destination, remove_destination, _output, log_message
from .common import CustomObject, CustomJSONEncoder


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
        d1 = {"x": 1}
        d2 = {"y": 2}
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
        with start_action(logger, "test"):
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
        with start_action(logger, "test"):
            Message.new(x=1).write(logger)
        # Now we should have x message, start action message, another x message
        # and finally finish message.
        logged = self.fromMessagesIndex(logger.messages, 1)
        self.assertEqual(
            (logged.startMessage, logged.endMessage),
            (logger.messages[1], logger.messages[3]),
        )

    def test_fromMessagesStartAndErrorFinish(self):
        """
        L{LoggedAction.fromMessages} finds the start and successful finish
        messages of an action and stores them in the result.
        """
        logger = MemoryLogger()
        try:
            with start_action(logger, "test"):
                raise KeyError()
        except KeyError:
            pass
        logged = self.fromMessagesIndex(logger.messages, 0)
        self.assertEqual(
            (logged.startMessage, logged.endMessage),
            (logger.messages[0], logger.messages[1]),
        )

    def test_fromMessagesStartNotFound(self):
        """
        L{LoggedAction.fromMessages} raises a L{ValueError} if a start message
        is not found.
        """
        logger = MemoryLogger()
        with start_action(logger, action_type="test"):
            pass
        self.assertRaises(ValueError, self.fromMessagesIndex, logger.messages[1:], 0)

    def test_fromMessagesFinishNotFound(self):
        """
        L{LoggedAction.fromMessages} raises a L{ValueError} if a finish message
        is not found.
        """
        logger = MemoryLogger()
        with start_action(logger, action_type="test"):
            pass
        with self.assertRaises(ValueError) as cm:
            self.fromMessagesIndex(logger.messages[:1], 0)
        self.assertEqual(cm.exception.args[0], "Missing end message of type test")

    def test_fromMessagesAddsChildMessages(self):
        """
        L{LoggedAction.fromMessages} adds direct child messages to the
        constructed L{LoggedAction}.
        """
        logger = MemoryLogger()
        # index 0:
        Message.new(x=1).write(logger)
        # index 1 - start action
        with start_action(logger, "test"):
            # index 2
            Message.new(x=2).write(logger)
            # index 3
            Message.new(x=3).write(logger)
        # index 4 - end action
        # index 5
        Message.new(x=4).write(logger)
        logged = self.fromMessagesIndex(logger.messages, 1)

        expectedChildren = [
            LoggedMessage(logger.messages[2]),
            LoggedMessage(logger.messages[3]),
        ]
        self.assertEqual(logged.children, expectedChildren)

    def test_fromMessagesAddsChildActions(self):
        """
        L{LoggedAction.fromMessages} recursively adds direct child actions to
        the constructed L{LoggedAction}.
        """
        logger = MemoryLogger()
        # index 0
        with start_action(logger, "test"):
            # index 1:
            with start_action(logger, "test2"):
                # index 2
                Message.new(message_type="end", x=2).write(logger)
            # index 3 - end action
            with start_action(logger, "test3"):
                # index 4
                pass
            # index 5 - end action
        # index 6 - end action
        logged = self.fromMessagesIndex(logger.messages, 0)

        self.assertEqual(logged.children[0], self.fromMessagesIndex(logger.messages, 1))
        self.assertEqual(
            logged.type_tree(), {"test": [{"test2": ["end"]}, {"test3": []}]}
        )

    def test_ofType(self):
        """
        L{LoggedAction.ofType} returns a list of L{LoggedAction} created by the
        specified L{ActionType}.
        """
        ACTION = ActionType("myaction", [], [], "An action!")
        logger = MemoryLogger()
        # index 0
        with start_action(logger, "test"):
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
        self.assertEqual(
            logged,
            [
                self.fromMessagesIndex(logger.messages, 1),
                self.fromMessagesIndex(logger.messages, 5),
            ],
        )

        # String-variant of ofType:
        logged2 = LoggedAction.ofType(logger.messages, "myaction")
        self.assertEqual(logged, logged2)

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
            with start_action(logger, "test"):
                # index 2
                Message.new(x=2).write(logger)
            # index 3 - end action
            # index 4
            Message.new(x=2).write(logger)
        # index 5 - end action

        loggedAction = LoggedAction.ofType(logger.messages, ACTION)[0]
        self.assertEqual(
            list(loggedAction.descendants()),
            [
                self.fromMessagesIndex(logger.messages, 1),
                LoggedMessage(logger.messages[2]),
                LoggedMessage(logger.messages[4]),
            ],
        )

    def test_succeeded(self):
        """
        If the action succeeded, L{LoggedAction.succeeded} will be true.
        """
        logger = MemoryLogger()
        with start_action(logger, "test"):
            pass
        logged = self.fromMessagesIndex(logger.messages, 0)
        self.assertTrue(logged.succeeded)

    def test_notSucceeded(self):
        """
        If the action failed, L{LoggedAction.succeeded} will be false.
        """
        logger = MemoryLogger()
        try:
            with start_action(logger, "test"):
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
        message = {"x": 1}
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
        self.assertEqual(
            logged,
            [LoggedMessage(logger.messages[0]), LoggedMessage(logger.messages[2])],
        )

        # Lookup by string type:
        logged2 = LoggedMessage.ofType(logger.messages, "mymessage")
        self.assertEqual(logged, logged2)

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


class ValidateLoggingTestsMixin(object):
    """
    Tests for L{validateLogging} and L{capture_logging}.
    """

    validate = None

    def test_decoratedFunctionCalledWithMemoryLogger(self):
        """
        The underlying function decorated with L{validateLogging} is called with
        a L{MemoryLogger} instance.
        """
        result = []

        class MyTest(TestCase):
            @self.validate(None)
            def test_foo(this, logger):
                result.append((this, logger.__class__))

        theTest = MyTest("test_foo")
        theTest.run()
        self.assertEqual(result, [(theTest, MemoryLogger)])

    def test_decorated_function_passthrough(self):
        """
        Additional arguments are passed to the underlying function.
        """
        result = []

        def another_wrapper(f):
            def g(this):
                f(this, 1, 2, c=3)

            return g

        class MyTest(TestCase):
            @another_wrapper
            @self.validate(None)
            def test_foo(this, a, b, logger, c=None):
                result.append((a, b, c))

        theTest = MyTest("test_foo")
        theTest.debug()
        self.assertEqual(result, [(1, 2, 3)])

    def test_newMemoryLogger(self):
        """
        The underlying function decorated with L{validateLogging} is called with
        a new L{MemoryLogger} every time the wrapper is called.
        """
        result = []

        class MyTest(TestCase):
            @self.validate(None)
            def test_foo(this, logger):
                result.append(logger)

        theTest = MyTest("test_foo")
        theTest.run()
        theTest.run()
        self.assertIsNot(result[0], result[1])

    def test_returns(self):
        """
        The result of the underlying function is returned by wrapper when called.
        """

        class MyTest(TestCase):
            @self.validate(None)
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
            @self.validate(None)
            def test_foo(self, logger):
                raise exc

        raised = None
        try:
            MyTest("test_foo").debug()
        except Exception as e:
            raised = e
        self.assertIs(exc, raised)

    def test_name(self):
        """
        The wrapper has the same name as the wrapped function.
        """

        class MyTest(TestCase):
            @self.validate(None)
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
            @self.validate(None)
            def runTest(self, logger):
                self.logger = logger
                logger.write({"message_type": "wrongmessage"}, MESSAGE._serializer)

        test = MyTest()
        with self.assertRaises(ValidationError) as context:
            test.debug()
        # Some reference to the reason:
        self.assertIn("wrongmessage", str(context.exception))
        # Some reference to which file caused the problem:
        self.assertIn("test_testing.py", str(context.exception))

    def test_addCleanupTracebacks(self):
        """
        When a test method is decorated with L{validateLogging} it has has a
        check unflushed tracebacks in the L{MemoryLogger} registered as a
        test cleanup.
        """

        class MyTest(TestCase):
            @self.validate(None)
            def runTest(self, logger):
                try:
                    1 / 0
                except ZeroDivisionError:
                    write_traceback(logger)

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

            @self.validate(assertLogging)
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

            @self.validate(assertLogging, 1, y=2)
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

            @self.validate(assertLogging)
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

            @self.validate(assertLogging)
            def runTest(self, logger):
                self.flushed = False
                try:
                    1 / 0
                except ZeroDivisionError:
                    write_traceback(logger)

        test = MyTest()
        test.run()
        self.assertTrue(test.flushed)


class ValidateLoggingTests(ValidateLoggingTestsMixin, TestCase):
    """
    Tests for L{validate_logging}.
    """

    validate = staticmethod(validate_logging)


class CaptureLoggingTests(ValidateLoggingTestsMixin, TestCase):
    """
    Tests for L{capture_logging}.
    """

    validate = staticmethod(capture_logging)

    def setUp(self):
        # Since we're not always calling the test method via the TestCase
        # infrastructure, sometimes cleanup methods are not called. This
        # means the original default logger is not restored. So we do so
        # manually. If the issue is a bug in capture_logging itself the
        # tests below will catch that.
        original_logger = _output._DEFAULT_LOGGER

        def cleanup():
            _output._DEFAULT_LOGGER = original_logger

        self.addCleanup(cleanup)

    def test_default_logger(self):
        """
        L{capture_logging} captures messages from logging that
        doesn't specify a L{Logger}.
        """

        class MyTest(TestCase):
            @capture_logging(None)
            def runTest(self, logger):
                Message.log(some_key=1234)
                self.logger = logger

        test = MyTest()
        test.run()
        self.assertEqual(test.logger.messages[0]["some_key"], 1234)

    def test_global_cleanup(self):
        """
        After the function wrapped with L{capture_logging} finishes,
        logging that doesn't specify a logger is logged normally.
        """

        class MyTest(TestCase):
            @capture_logging(None)
            def runTest(self, logger):
                pass

        test = MyTest()
        test.run()
        messages = []
        add_destination(messages.append)
        self.addCleanup(remove_destination, messages.append)
        Message.log(some_key=1234)
        self.assertEqual(messages[0]["some_key"], 1234)

    def test_global_cleanup_exception(self):
        """
        If the function wrapped with L{capture_logging} throws an exception,
        logging that doesn't specify a logger is logged normally.
        """

        class MyTest(TestCase):
            @capture_logging(None)
            def runTest(self, logger):
                raise RuntimeError()

        test = MyTest()
        test.run()
        messages = []
        add_destination(messages.append)
        self.addCleanup(remove_destination, messages.append)
        Message.log(some_key=1234)
        self.assertEqual(messages[0]["some_key"], 1234)

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
            (False, [(test, "Do not run this test.")], [], []),
        )


class JSONEncodingTests(TestCase):
    """Tests for L{capture_logging} JSON encoder support."""

    @skipUnless(np, "NumPy is not installed.")
    @capture_logging(None)
    def test_default_JSON_encoder(self, logger):
        """
        L{capture_logging} validates using L{EliotJSONEncoder} by default.
        """
        # Default JSON encoder can't handle NumPy:
        log_message(message_type="hello", number=np.uint32(12))

    @capture_logging(None, encoder_=CustomJSONEncoder)
    def test_custom_JSON_encoder(self, logger):
        """
        L{capture_logging} can be called with a custom JSON encoder, which is then
        used for validation.
        """
        # Default JSON encoder can't handle this custom object:
        log_message(message_type="hello", object=CustomObject())


MESSAGE1 = MessageType(
    "message1", [Field.forTypes("x", [int], "A number")], "A message for testing."
)
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
        self.assertRaises(AssertionError, assertHasMessage, test, logger, MESSAGE2)

    def test_returnsIfMessagesOfType(self):
        """
        L{assertHasMessage} returns the first message of the given L{MessageType}.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        MESSAGE1(x=123).write(logger)
        self.assertEqual(
            assertHasMessage(test, logger, MESSAGE1),
            LoggedMessage.ofType(logger.messages, MESSAGE1)[0],
        )

    def test_failIfNotSubset(self):
        """
        L{assertHasMessage} raises L{AssertionError} if the found message doesn't
        contain the given fields.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        MESSAGE1(x=123).write(logger)
        self.assertRaises(
            AssertionError, assertHasMessage, test, logger, MESSAGE1, {"x": 24}
        )

    def test_returnsIfSubset(self):
        """
        L{assertHasMessage} returns the first message of the given L{MessageType} if
        it contains the given fields.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        MESSAGE1(x=123).write(logger)
        self.assertEqual(
            assertHasMessage(test, logger, MESSAGE1, {"x": 123}),
            LoggedMessage.ofType(logger.messages, MESSAGE1)[0],
        )


ACTION1 = ActionType(
    "action1",
    [Field.forTypes("x", [int], "A number")],
    [Field.forTypes("result", [int], "A number")],
    "A action for testing.",
)
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
        with ACTION1(logger, x=123):
            pass
        self.assertRaises(AssertionError, assertHasAction, test, logger, ACTION2, True)

    def test_failIfWrongSuccessStatus(self):
        """
        L{assertHasAction} raises L{AssertionError} if the given success status does
        not match that of the found actions.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        with ACTION1(logger, x=123):
            pass
        try:
            with ACTION2(logger):
                1 / 0
        except ZeroDivisionError:
            pass
        self.assertRaises(AssertionError, assertHasAction, test, logger, ACTION1, False)
        self.assertRaises(AssertionError, assertHasAction, test, logger, ACTION2, True)

    def test_returnsIfMessagesOfType(self):
        """
        A successful L{assertHasAction} returns the first message of the given
        L{ActionType}.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        with ACTION1(logger, x=123):
            pass
        self.assertEqual(
            assertHasAction(test, logger, ACTION1, True),
            LoggedAction.ofType(logger.messages, ACTION1)[0],
        )

    def test_failIfNotStartSubset(self):
        """
        L{assertHasAction} raises L{AssertionError} if the found action doesn't
        contain the given start fields.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        with ACTION1(logger, x=123):
            pass
        self.assertRaises(
            AssertionError, assertHasAction, test, logger, ACTION1, True, {"x": 24}
        )

    def test_failIfNotEndSubset(self):
        """
        L{assertHasAction} raises L{AssertionError} if the found action doesn't
        contain the given end fields.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        with ACTION1(logger, x=123) as act:
            act.addSuccessFields(result=5)
        self.assertRaises(
            AssertionError,
            assertHasAction,
            test,
            logger,
            ACTION1,
            True,
            startFields={"x": 123},
            endFields={"result": 24},
        )

    def test_returns(self):
        """
        A successful L{assertHasAction} returns the first message of the given
        L{ActionType} after doing all validation.
        """
        test = self.UnitTest()
        logger = MemoryLogger()
        with ACTION1(logger, x=123) as act:
            act.addSuccessFields(result=5)
        self.assertEqual(
            assertHasAction(test, logger, ACTION1, True, {"x": 123}, {"result": 5}),
            LoggedAction.ofType(logger.messages, ACTION1)[0],
        )


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


class LowLevelTestingHooks(TestCase):
    """Tests for lower-level APIs for setting up MemoryLogger."""

    @capture_logging(None)
    def test_swap_logger(self, logger):
        """C{swap_logger} swaps out the current logger."""
        new_logger = MemoryLogger()
        old_logger = swap_logger(new_logger)
        Message.log(message_type="hello")

        # We swapped out old logger for new:
        self.assertIs(old_logger, logger)
        self.assertEqual(new_logger.messages[0]["message_type"], "hello")

        # Now restore old logger:
        intermediate_logger = swap_logger(old_logger)
        Message.log(message_type="goodbye")
        self.assertIs(intermediate_logger, new_logger)
        self.assertEqual(logger.messages[0]["message_type"], "goodbye")

    def test_check_for_errors_unflushed_tracebacks(self):
        """C{check_for_errors} raises on unflushed tracebacks."""
        logger = MemoryLogger()

        # No errors initially:
        check_for_errors(logger)

        try:
            1 / 0
        except ZeroDivisionError:
            write_traceback(logger)
        logger.flush_tracebacks(ZeroDivisionError)

        # Flushed tracebacks don't count:
        check_for_errors(logger)

        # But unflushed tracebacks do:
        try:
            raise RuntimeError
        except RuntimeError:
            write_traceback(logger)
        with self.assertRaises(UnflushedTracebacks):
            check_for_errors(logger)

    def test_check_for_errors_validation(self):
        """C{check_for_errors} raises on validation errors."""
        logger = MemoryLogger()
        logger.write({"x": 1, "message_type": "mem"})

        # No errors:
        check_for_errors(logger)

        # Now long something unserializable to JSON:
        logger.write({"message_type": object()})
        with self.assertRaises(TypeError):
            check_for_errors(logger)
