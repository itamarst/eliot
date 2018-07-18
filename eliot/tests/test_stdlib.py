"""Tests for standard library logging integration."""

from unittest import TestCase
import logging
import traceback

from ..testing import assertContainsFields, capture_logging
from ..stdlib import EliotHandler
from .test_traceback import assert_expected_traceback


class StdlibTests(TestCase):
    """Tests for stdlib integration."""

    @capture_logging(None)
    def test_handler(self, logger):
        """The EliotHandler routes messages to Eliot."""
        stdlib_logger = logging.getLogger("eliot-test")
        stdlib_logger.setLevel(logging.DEBUG)
        handler = EliotHandler()
        stdlib_logger.addHandler(handler)
        stdlib_logger.info("hello")
        stdlib_logger.warning("ono")
        message = logger.messages[0]
        assertContainsFields(
            self, message, {
                "message_type": "eliot:stdlib",
                "log_level": "INFO",
                "message": "hello",
                "logger": "eliot-test"
            }
        )
        message = logger.messages[1]
        assertContainsFields(
            self, message, {
                "message_type": "eliot:stdlib",
                "log_level": "WARNING",
                "message": "ono",
                "logger": "eliot-test"
            }
        )

    @capture_logging(None)
    def test_traceback(self, logger):
        """The EliotHandler routes tracebacks to Eliot."""
        stdlib_logger = logging.getLogger("eliot-test2")
        stdlib_logger.setLevel(logging.DEBUG)
        handler = EliotHandler()
        stdlib_logger.addHandler(handler)
        try:
            raise RuntimeError()
        except Exception as e:
            exception = e
            expected_traceback = traceback.format_exc()
            stdlib_logger.exception("ono")
        message = logger.messages[0]
        assertContainsFields(
            self, message, {
                "message_type": "eliot:stdlib",
                "log_level": "ERROR",
                "message": "ono",
                "logger": "eliot-test2"
            }
        )
        assert_expected_traceback(
            self, logger, logger.messages[1], exception, expected_traceback
        )
