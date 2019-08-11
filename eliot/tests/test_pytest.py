"""Tests for py.test plugins/fixtures."""


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
