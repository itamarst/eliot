"""
Tests for L{eliot.journald}.
"""

from os import getpid
from unittest import skipUnless, TestCase
from subprocess import check_output, CalledProcessError, STDOUT

from .._bytesjson import loads
from ..journald import sd_journal_send


def _journald_available():
    """
    :return: Boolean indicating whether journald is available to use.
    """
    try:
        check_output(["journalctl", "-b"], stderr=STDOUT)
    except CalledProcessError:
        return False
    return True


class SdJournaldSendTests(TestCase):
    """
    Functional tests for L{sd_journal_send}.
    """
    @skipUnless(_journald_available(),
                "journald unavailable or inactive on this machine.")
    def send_journald_message(self, message):
        """
        Log a journald message, extract resulting message from journald.

        @param message: Dictionary to pass as keyword arguments to
            C{sd_journal_send}.

        @return: Last journald JSON message from this process as a dictionary.
        """
        sd_journal_send(**message)
        messages = check_output(
            [b"journalctl", b"-a", b"-o", b"json", b"_PID=%d" % (getpid(),)])
        return loads(messages.splitlines()[-1])

    def assert_roundtrip(self, value):
        """
        Write a value as a C{MESSAGE} field, assert it is output.

        @param value: Value to write as unicode.
        """
        result = self.send_journald_message({"MESSAGE": value})
        self.assertEqual(value, result["MESSAGE"])

    def test_message(self):
        """
        L{sd_journal_send} can write a C{MESSAGE} field.
        """
        self.assert_roundtrip(b"hello")

    def test_percent(self):
        """
        L{sd_journal_send} can write a C{MESSAGE} field with a percent.

        Underlying C API calls does printf formatting so this is a
        plausible failure mode.
        """
        self.assert_roundtrip(b"hello%world")

    def test_large(self):
        """
        L{sd_journal_send} can write a C{MESSAGE} field with a large message.
        """
        self.assert_roundtrip(b"hello world" * 20000)

    def test_multiple_fields(self):
        """
        L{sd_journal_send} can send multiple fields.
        """
        result = self.send_journald_message({"MESSAGE": b"hello",
                                             "BONUS_FIELD": b"world"})
        self.assertEqual((b"hello", b"world"),
                         (result["MESSAGE"], result["BONUS_FIELD"]))
