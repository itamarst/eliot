"""
Tests for L{eliot.journald}.
"""

try:
    import cffi
except ImportError:
    cffi = None
else:
    from ..journald import sd_journal_send, JournaldDestination

from os import getpid, strerror
from unittest import skipUnless, TestCase
from subprocess import check_output, CalledProcessError, STDOUT
from errno import EINVAL

from .._bytesjson import loads
from .._output import MemoryLogger
from .._message import TASK_UUID_FIELD
from .. import start_action, Message, write_traceback


def _journald_available():
    """
    :return: Boolean indicating whether journald is available to use.
    """
    if cffi is None:
        return False
    try:
        check_output(["journalctl", "-b"], stderr=STDOUT)
    except CalledProcessError:
        return False
    return True


def last_journald_message():
    """
    @return: Last journald message from this process as a dictionary in
         journald JSON format.
    """
    messages = check_output(
        [b"journalctl", b"-a", b"-o", b"json", b"_PID=%d" % (getpid(),)])
    return loads(messages.splitlines()[-1])


class SdJournaldSendTests(TestCase):
    """
    Functional tests for L{sd_journal_send}.
    """
    @skipUnless(_journald_available(),
                "journald unavailable or inactive on this machine.")
    def setUp(self):
        pass

    def assert_roundtrip(self, value):
        """
        Write a value as a C{MESSAGE} field, assert it is output.

        @param value: Value to write as unicode.
        """
        sd_journal_send(MESSAGE=value)
        result = last_journald_message()
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
        sd_journal_send(MESSAGE=b"hello", BONUS_FIELD=b"world")
        result = last_journald_message()
        self.assertEqual((b"hello", b"world"),
                         (result["MESSAGE"], result["BONUS_FIELD"]))

    def test_error(self):
        """
        L{sd_journal_send} raises an error when it gets a non-0 result
        from the underlying API.
        """
        with self.assertRaises(IOError) as context:
            sd_journal_send(**{"": b"123"})
        exc = context.exception
        self.assertEqual((exc.errno, exc.strerror), (EINVAL, strerror(EINVAL)))


class JournaldDestinationTests(TestCase):
    """
    Tests for L{JournaldDestination}.
    """
    @skipUnless(_journald_available(),
                "journald unavailable or inactive on this machine.")
    def setUp(self):
        self.destination = JournaldDestination()
        self.logger = MemoryLogger()

    def test_json(self):
        """
        The message is stored as JSON in the MESSAGE field.
        """
        Message.new(hello="world", key=123).write(self.logger)
        message = self.logger.messages[0]
        self.destination(message)
        self.assertEqual(loads(last_journald_message()["MESSAGE"]), message)

    def assert_field_for(self, message, field_name, field_value):
        """
        If the given message is logged by Eliot, the given journald field has
        the expected value.

        @param message: Dictionary to log.
        @param field_name: Journald field name to check.
        @param field_value: Expected value for the field.
        """
        self.destination(message)
        self.assertEqual(last_journald_message()[field_name], field_value)

    def test_action_type(self):
        """
        The C{action_type} is stored in the ELIOT_TYPE field.
        """
        action_type = "test:type"
        start_action(self.logger, action_type=action_type)
        self.assert_field_for(self.logger.messages[0], "ELIOT_TYPE",
                              action_type)

    def test_message_type(self):
        """
        The C{message_type} is stored in the ELIOT_TYPE field.
        """
        message_type = "test:type:message"
        Message.new(message_type=message_type).write(self.logger)
        self.assert_field_for(self.logger.messages[0], "ELIOT_TYPE",
                              message_type)

    def test_no_type(self):
        """
        An empty string is stored in ELIOT_TYPE if no type is known.
        """
        Message.new().write(self.logger)
        self.assert_field_for(self.logger.messages[0], "ELIOT_TYPE", "")

    def test_uuid(self):
        """
        The task UUID is stored in the ELIOT_TASK field.
        """
        start_action(self.logger, action_type="xxx")
        self.assert_field_for(self.logger.messages[0], "ELIOT_TASK",
                              self.logger.messages[0][TASK_UUID_FIELD])

    def test_info_priorities(self):
        """
        Untyped messages, action start, successful action end, random typed
        message all get priority 6 ("info").
        """
        with start_action(self.logger, action_type="xxx"):
            Message.new(message_type="msg").write(self.logger)
            Message.new(x=123).write(self.logger)
        priorities = []
        for message in self.logger.messages:
            self.destination(message)
            priorities.append(last_journald_message()["PRIORITY"])
        self.assertEqual(priorities, [u"6", u"6", u"6", u"6"])

    def test_error_priority(self):
        """
        A failed action gets priority 3 ("error").
        """
        try:
            with start_action(self.logger, action_type="xxx"):
                raise ZeroDivisionError()
        except ZeroDivisionError:
            pass
        self.assert_field_for(self.logger.messages[-1], "PRIORITY", u"3")

    def test_critical_priority(self):
        """
        A traceback gets priority 2 ("critical").
        """
        try:
            raise ZeroDivisionError()
        except ZeroDivisionError:
            write_traceback(logger=self.logger)
        self.assert_field_for(self.logger.serialize()[-1], "PRIORITY", u"2")

