"""
Tests for L{eliot._traceback}.
"""

from __future__ import unicode_literals

from unittest import TestCase, SkipTest
import traceback
import sys

try:
    from twisted.python.failure import Failure
except ImportError:
    Failure = None

from .._traceback import writeTraceback, writeFailure, _writeTracebackMessage
from ..testing import assertContainsFields, validateLogging


class TracebackLoggingTests(TestCase):
    """
    Tests for L{writeTraceback} and L{writeFailure}.
    """
    @validateLogging(None)
    def test_writeTraceback(self, logger):
        """
        L{writeTraceback} writes the current traceback to the log.
        """
        def raiser():
            raise RuntimeError("because")
        try:
            raiser()
        except Exception as e:
            expectedTraceback = traceback.format_exc()
            writeTraceback(logger, "some:system")
        lines = expectedTraceback.split("\n")
        # Remove source code lines:
        expectedTraceback = "\n".join(
            [l for l in lines if not l.startswith("    ")])
        message = logger.messages[0]
        assertContainsFields(self, message,
                             {"system": "some:system",
                              "message_type": "eliot:traceback",
                              "exception": RuntimeError,
                              "reason": e,
                              "traceback": expectedTraceback})
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
            writeFailure(failure, logger, "some:system")
        message = logger.messages[0]
        assertContainsFields(self, message,
                             {"system": "some:system",
                              "message_type": "eliot:traceback",
                              "exception": RuntimeError,
                              "reason": failure.value,
                              "traceback": expectedTraceback})
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
            result = writeFailure(Failure(), logger, "some:system")
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
        _writeTracebackMessage(logger, "sys", *exc_info)
        serialized = logger.serialize()[0]
        assertContainsFields(self, serialized,
                             {"exception": "exceptions.KeyError",
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
        _writeTracebackMessage(logger, "sys", *exc_info)
        self.assertEqual(logger.serialize()[0]["reason"],
                         "eliot: unknown, unicode() raised exception")
        logger.flushTracebacks(BadException)
