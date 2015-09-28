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

        @return: C{list} of decoded journald JSON messages from this
            process.
        """
        cursor = check_output([b"journalctl", b"--show-cursor"])
        sd_journal_send(**message)
        messages = check_output([b"journalctl", b"-c", cursor,
                                 b"_PID=%d" % (getpid(),),
                                 b"-o", b"json"])
        return list(loads(m) for m in messages)

    def assert_roundtrip(self, value):
        """
        Write a value as a C{MESSAGE} field, assert it is output.

        @param value: Value to write as unicode.
        """
        results = self.send_journald_message({"MESSAGE": value})
        self.assertIn(value, [m["MESSAGE"] for m in results])

    def test_message(self):
        """
        L{sd_journal_send} can write a C{MESSAGE} field.
        """
        self.assert_roundtrip(u"hello")

    def test_percent(self):
        """
        L{sd_journal_send} can write a C{MESSAGE} field with a percent.

        Underlying C API calls does printf formatting so this is a
        plausible failure mode.
        """
        self.assert_roundtrip(u"hello%world")

    def test_large(self):
        """
        L{sd_journal_send} can write a C{MESSAGE} field with a large message.
        """
        self.assert_roundtrip(u"hello world" * 30000)

    def test_unicode(self):
        """
        L{sd_journal_send} can write a C{MESSAGE} field with Unicode
        characters not encodable in ASCII.
        """
        self.assert_roundtrip(u"hello \u1234")

    def test_multiple_fields(self):
        """
        L{sd_journal_send} can send multiple fields.
        """
        results = self.send_journald_message({"MESSAGE": u"hello",
                                              "BONUS_FIELD": u"world"})
        self.assertIn((u"hello", u"world"),
                      [(m["MESSAGE"], m["BONUS_FIELD"]) for m in results])
