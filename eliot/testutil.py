"""Utilities for testing."""

import json
from unittest import TestCase
from typing import Type

from .json import EliotJSONEncoder
from ._message import MESSAGE_TYPE_FIELD
from ._traceback import REASON_FIELD, class_fqpn
from ._util import exclusively


__all__ = ["TestingDestination", "UnexpectedTracebacks", "logs_for_pyunit"]


class UnexpectedTracebacks(Exception):
    """
    A test had some tracebacks logged which were not marked as expected.

    If you expected the traceback then you will need to flush it using
    C{TestingDestination.flush_tracebacks}.
    """


class TestingDestination:
    """
    A destination that stores messages for testing purposes.

    Unexpected tracebacks are considered errors (your code logging a traceback
    typically indicates a bug), so you will need to remove expected tracebacks
    by calling C{remove_expected_tracebacks}.
    """

    def __init__(self, encode, decode):
        """
        @param encode: Take an unserialized message, serialize it.
        @param decode: Take an serialized message, deserialize it.
        """
        self.messages = []
        self._traceback_messages = []
        self._encode = encode
        self._decode = decode

    @exclusively
    def write(self, message):
        if message.get(MESSAGE_TYPE_FIELD) == "eliot:traceback":
            self._traceback_messages.append(message)
        self.messages.append(self._decode(self._encode(message)))

    @exclusively
    def remove_expected_tracebacks(self, exceptionType: Type[Exception]):
        """
        Remove all logged tracebacks whose exception is of the given type.

        This means they are expected tracebacks and should not cause the test
        to fail.

        @param exceptionType: A subclass of L{Exception}.

        @return: C{list} of flushed messages.
        """
        result = []
        remaining = []
        for message in self._traceback_messages:
            if message[REASON_FIELD] == class_fqpn(exceptionType):
                result.append(message)
            else:
                remaining.append(message)
        self.traceback_messages = remaining
        return result

    def _ensure_no_bad_messages(self):
        """
        Raise L{UnexpectedTracebacks} if there are any unexpected tracebacks.

        Raise L{ValueError} if there are serialization failures from the Eliot
        type system, or serialization errors from the encoder/decoder
        (typically JSON).

        If you expect a traceback to be logged, remove it using
        C{remove_expected_tracebacks}.
        """
        if self._traceback_messages:
            raise UnexpectedTracebacks(self._traceback_messages)
        serialization_failures = [
            m
            for m in self.messages
            if m.get(MESSAGE_TYPE_FIELD)
            in ("eliot:serialization_failure", "eliot:destination_failure")
        ]
        if serialization_failures:
            raise ValueError(serialization_failures)


def _capture_logs(addfinalizer, encode, decode):
    test_dest = TestingDestination(encode, decode)
    from . import add_destinations, remove_destination

    add_destinations(test_dest)
    addfinalizer(remove_destination, test_dest)
    addfinalizer(test_dest._ensure_no_bad_messages)

    return test_dest


def logs_for_pyunit(
    test_case: TestCase, encode=EliotJSONEncoder().encode, decode=json.loads
) -> TestingDestination:
    """Capture the logs for a C{unittest.TestCase}.

        1. Captures all log messages.

        2. At the end of the test, raises an exception if there are any
           unexpected tracebacks, or any of the messages couldn't be
           serialized.

    @returns: The L{TestingDestination} that will capture the log messages.
    """
    return _capture_logs(test_case.addCleanup, encode, decode)
