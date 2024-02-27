"""
Tests for L{eliot.journald}.
"""
from os import getpid, strerror
from unittest import skipUnless, TestCase
from subprocess import check_output, CalledProcessError, STDOUT
from errno import EINVAL
from sys import argv
from uuid import uuid4
from time import sleep
from json import loads

from .._output import MemoryLogger
from .._message import TASK_UUID_FIELD
from .. import start_action, Message, write_traceback

try:
    from ..journald import sd_journal_send, JournaldDestination
except ImportError:
    sd_journal_send = None


def _journald_available():
    """
    :return: Boolean indicating whether journald is available to use.
    """
    if sd_journal_send is None:
        return False
    try:
        check_output(["journalctl", "-b", "-n1"], stderr=STDOUT)
    except (OSError, CalledProcessError):
        return False
    return True


def last_journald_message():
    """
    @return: Last journald message from this process as a dictionary in
         journald JSON format.
    """
    # It may take a little for messages to actually reach journald, so we
    # write out marker message and wait until it arrives. We can then be
    # sure the message right before it is the one we want.
    marker = str(uuid4())
    sd_journal_send(MESSAGE=marker.encode("ascii"))
    for i in range(500):
        messages = check_output(
            [
                b"journalctl",
                b"-a",
                b"-o",
                b"json",
                b"-n2",
                b"_PID=" + str(getpid()).encode("ascii"),
            ]
        )
        messages = [loads(m) for m in messages.splitlines()]
        if len(messages) == 2 and messages[1]["MESSAGE"] == marker:
            return messages[0]
        sleep(0.01)
    raise RuntimeError("Message never arrived?!")


class SdJournaldSendTests(TestCase):
    """
    Functional tests for L{sd_journal_send}.
    """

    @skipUnless(
        _journald_available(), "journald unavailable or inactive on this machine."
    )
    def setUp(self):
        pass

    def assert_roundtrip(self, value):
        """
        Write a value as a C{MESSAGE} field, assert it is output.

        @param value: Value to write as unicode.
        """
        sd_journal_send(MESSAGE=value)
        result = last_journald_message()
        self.assertEqual(value, result["MESSAGE"].encode("utf-8"))

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
        self.assertEqual(
            (b"hello", b"world"),
            (result["MESSAGE"].encode("ascii"), result["BONUS_FIELD"].encode("ascii")),
        )

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

    @skipUnless(
        _journald_available(), "journald unavailable or inactive on this machine."
    )
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
        self.assert_field_for(self.logger.messages[0], "ELIOT_TYPE", action_type)

    def test_message_type(self):
        """
        The C{message_type} is stored in the ELIOT_TYPE field.
        """
        message_type = "test:type:message"
        Message.new(message_type=message_type).write(self.logger)
        self.assert_field_for(self.logger.messages[0], "ELIOT_TYPE", message_type)

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
        self.assert_field_for(
            self.logger.messages[0],
            "ELIOT_TASK",
            self.logger.messages[0][TASK_UUID_FIELD],
        )

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
        self.assertEqual(priorities, ["6", "6", "6", "6"])

    def test_error_priority(self):
        """
        A failed action gets priority 3 ("error").
        """
        try:
            with start_action(self.logger, action_type="xxx"):
                raise ZeroDivisionError()
        except ZeroDivisionError:
            pass
        self.assert_field_for(self.logger.messages[-1], "PRIORITY", "3")

    def test_critical_priority(self):
        """
        A traceback gets priority 2 ("critical").
        """
        try:
            raise ZeroDivisionError()
        except ZeroDivisionError:
            write_traceback(logger=self.logger)
        self.assert_field_for(self.logger.serialize()[-1], "PRIORITY", "2")

    def test_identifier(self):
        """
        C{SYSLOG_IDENTIFIER} defaults to C{os.path.basename(sys.argv[0])}.
        """
        identifier = "/usr/bin/testing123"
        try:
            original = argv[0]
            argv[0] = identifier
            # Recreate JournaldDestination with the newly set argv[0].
            self.destination = JournaldDestination()
            Message.new(message_type="msg").write(self.logger)
            self.assert_field_for(
                self.logger.messages[0], "SYSLOG_IDENTIFIER", "testing123"
            )
        finally:
            argv[0] = original
