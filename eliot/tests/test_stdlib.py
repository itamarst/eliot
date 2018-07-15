"""Tests for standard library logging integration."""

from unittest import TestCase
import logging

from ..testing import assertContainsFields, capture_logging
from ..stdlib import EliotHandler


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
        stdlib_logger.warn("ono")
        message = logger.messages[0]
        assertContainsFields(self, message, {"message_type": "eliot:stdlib",
                                             "log_level": "INFO",
                                             "message": "hello",
                                             "logger": "eliot-test"})
        message = logger.messages[1]
        assertContainsFields(self, message, {"message_type": "eliot:stdlib",
                                             "log_level": "WARNING",
                                             "message": "ono",
                                             "logger": "eliot-test"})
