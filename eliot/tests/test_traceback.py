"""
Tests for L{eliot._traceback}.
"""

from __future__ import unicode_literals

from unittest import TestCase, SkipTest
from warnings import catch_warnings, simplefilter
import traceback
import sys

try:
    from twisted.python.failure import Failure
except ImportError:
    Failure = None

from .._traceback import write_traceback, writeFailure, _writeTracebackMessage
from ..testing import (
    assertContainsFields,
    validateLogging,
    capture_logging,
    MemoryLogger,
)
from .._errors import register_exception_extractor
from .test_action import make_error_extraction_tests


class TracebackLoggingTests(TestCase):
    """
    Tests for L{write_traceback} and L{writeFailure}.
    """

    @validateLogging(None)
    def test_write_traceback_implicit(self, logger):
        """
        L{write_traceback} with no arguments writes the current traceback to
        the log.
        """
        e = None

        def raiser():
            raise RuntimeError("because")

        try:
            raiser()
        except Exception as exception:
            expected_traceback = traceback.format_exc()
            write_traceback(logger)
            e = exception
        self.assert_expected_traceback(logger, e, expected_traceback)

    @validateLogging(None)
    def test_write_traceback_explicit(self, logger):
        """
        L{write_traceback} with explicit arguments writes the given traceback
        to the log.
        """
        e = None

        def raiser():
            raise RuntimeError("because")

        try:
            raiser()
        except Exception as exception:
            expected_traceback = traceback.format_exc()
            write_traceback(logger, exc_info=sys.exc_info())
            e = exception
        self.assert_expected_traceback(logger, e, expected_traceback)

    def assert_expected_traceback(self, logger, exception, expected_traceback):
        """Assert we logged the given exception and the expected traceback."""
        lines = expected_traceback.split("\n")
        # Remove source code lines:
        expected_traceback = "\n".join(
            [l for l in lines if not l.startswith("    ")]
        )
        message = logger.messages[0]
        assertContainsFields(
            self, message, {
                "message_type": "eliot:traceback",
                "exception": RuntimeError,
                "reason": exception,
                "traceback": expected_traceback
            }
        )
        logger.flushTracebacks(RuntimeError)

    @capture_logging(None)
    def test_writeTracebackDefaultLogger(self, logger):
        """
        L{write_traceback} writes to the default log, if none is
        specified.
        """

        def raiser():
            raise RuntimeError("because")

        try:
            raiser()
        except Exception:
            write_traceback()

        message = logger.messages[0]
        assertContainsFields(
            self, message, {
                "message_type": "eliot:traceback"
            }
        )
        logger.flushTracebacks(RuntimeError)

    @validateLogging(None)
    def test_writeFailure(self, logger):
        """
        L{writeFailure} writes a L{Failure} to the log.
        """
        if Failure is None:
            raise SkipTest("Twisted unavailable")

        try:
            raise RuntimeError("because")
        except:
            failure = Failure()
            expectedTraceback = failure.getBriefTraceback()
            writeFailure(failure, logger)
        message = logger.messages[0]
        assertContainsFields(
            self, message, {
                "message_type": "eliot:traceback",
                "exception": RuntimeError,
                "reason": failure.value,
                "traceback": expectedTraceback
            }
        )
        logger.flushTracebacks(RuntimeError)

    @capture_logging(None)
    def test_writeFailureDefaultLogger(self, logger):
        """
        L{writeFailure} writes to the default log, if none is
        specified.
        """
        if Failure is None:
            raise SkipTest("Twisted unavailable")

        try:
            raise RuntimeError("because")
        except:
            failure = Failure()
            writeFailure(failure)
        message = logger.messages[0]
        assertContainsFields(
            self, message, {
                "message_type": "eliot:traceback"
            }
        )
        logger.flushTracebacks(RuntimeError)

    @validateLogging(None)
    def test_writeFailureResult(self, logger):
        """
        L{writeFailure} returns C{None}.
        """
        if Failure is None:
            raise SkipTest("Twisted unavailable")

        try:
            raise RuntimeError("because")
        except:
            result = writeFailure(Failure(), logger)
        self.assertIs(result, None)
        logger.flushTracebacks(RuntimeError)

    @validateLogging(None)
    def test_serialization(self, logger):
        """
        L{_writeTracebackMessage} serializes exceptions to string values and
        types to FQPN.
        """
        try:
            raise KeyError(123)
        except:
            exc_info = sys.exc_info()
        _writeTracebackMessage(logger, *exc_info)
        serialized = logger.serialize()[0]
        assertContainsFields(
            self, serialized, {
                "exception": "%s.KeyError" % (KeyError.__module__, ),
                "reason": "123"
            }
        )
        logger.flushTracebacks(KeyError)

    @validateLogging(None)
    def test_badException(self, logger):
        """
        L{_writeTracebackMessage} logs a message even if given a bad exception.
        """

        class BadException(Exception):
            def __str__(self):
                raise TypeError()

        try:
            raise BadException()
        except BadException:
            exc_info = sys.exc_info()
        _writeTracebackMessage(logger, *exc_info)
        self.assertEqual(
            logger.serialize()[0]["reason"],
            "eliot: unknown, unicode() raised exception"
        )
        logger.flushTracebacks(BadException)


def get_traceback_messages(exception):
    """
    Given an exception instance generate a traceback Eliot message.
    """
    logger = MemoryLogger()
    try:
        raise exception
    except exception.__class__:
        write_traceback(logger)
    # MemoryLogger.validate() mutates messages:
    # https://github.com/ScatterHQ/eliot/issues/243
    messages = [message.copy() for message in logger.messages]
    logger.validate()
    return messages


class TracebackExtractionTests(
    make_error_extraction_tests(get_traceback_messages)
):
    """
    Error extraction tests for tracebacks.
    """

    def test_regular_fields(self):
        """
        The normal traceback fields are still present when error
        extraction is used.
        """

        class MyException(Exception):
            pass

        register_exception_extractor(MyException, lambda e: {"key": e.args[0]})
        exception = MyException("because")
        messages = get_traceback_messages(exception)
        assertContainsFields(
            self, messages[0], {
                "message_type": "eliot:traceback",
                "reason": exception,
                "exception": MyException
            }
        )
