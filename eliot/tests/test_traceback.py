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

from .._traceback import writeTraceback, writeFailure, _writeTracebackMessage
from ..testing import (
    assertContainsFields, validateLogging, capture_logging,
    MemoryLogger,
)
from .test_action import make_error_extraction_tests


class TracebackLoggingTests(TestCase):
    """
    Tests for L{writeTraceback} and L{writeFailure}.
    """
    @validateLogging(None)
    def test_writeTraceback(self, logger):
        """
        L{writeTraceback} writes the current traceback to the log.
        """
        e = None
        def raiser():
            raise RuntimeError("because")
        try:
            raiser()
        except Exception as exception:
            expectedTraceback = traceback.format_exc()
            writeTraceback(logger)
            e = exception
        lines = expectedTraceback.split("\n")
        # Remove source code lines:
        expectedTraceback = "\n".join(
            [l for l in lines if not l.startswith("    ")])
        message = logger.messages[0]
        assertContainsFields(self, message,
                             {"message_type": "eliot:traceback",
                              "exception": RuntimeError,
                              "reason": e,
                              "traceback": expectedTraceback})
        logger.flushTracebacks(RuntimeError)


    @capture_logging(None)
    def test_writeTracebackDefaultLogger(self, logger):
        """
        L{writeTraceback} writes to the default log, if none is
        specified.
        """
        def raiser():
            raise RuntimeError("because")
        try:
            raiser()
        except Exception:
            writeTraceback()

        message = logger.messages[0]
        assertContainsFields(self, message,
                             {"message_type": "eliot:traceback"})
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
        assertContainsFields(self, message,
                             {"message_type": "eliot:traceback",
                              "exception": RuntimeError,
                              "reason": failure.value,
                              "traceback": expectedTraceback})
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
        assertContainsFields(self, message,
                             {"message_type": "eliot:traceback"})
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
        assertContainsFields(self, serialized,
                             {"exception":
                              "%s.KeyError" % (KeyError.__module__,),
                              "reason": "123"})
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
        self.assertEqual(logger.serialize()[0]["reason"],
                         "eliot: unknown, unicode() raised exception")
        logger.flushTracebacks(BadException)


    def test_systemDeprecatedWriteTraceback(self):
        """
        L{writeTraceback} warns with C{DeprecationWarning} if a C{system}
        argument is passed in.
        """
        logger = MemoryLogger()
        with catch_warnings(record=True) as warnings:
            simplefilter("always")
            try:
                raise Exception()
            except:
                writeTraceback(logger, "system")
            self.assertEqual(warnings[-1].category, DeprecationWarning)


    def test_systemDeprecatedWriteFailure(self):
        """
        L{writeTraceback} warns with C{DeprecationWarning} if a C{system}
        argument is passed in.
        """
        if Failure is None:
            raise SkipTest("Twisted unavailable")

        logger = MemoryLogger()
        with catch_warnings(record=True) as warnings:
            simplefilter("always")
            try:
                raise Exception()
            except:
                writeFailure(Failure(), logger, "system")
            self.assertEqual(warnings[-1].category, DeprecationWarning)


def get_traceback_messages(exception):
    """
    Given an exception instance generate a traceback Eliot message.
    """
    logger = MemoryLogger()
    try:
        raise exception
    except exception.__class__:
        writeTraceback(logger)
    return logger.messages
TracebackExtractionTests = make_error_extraction_tests(get_traceback_messages)

