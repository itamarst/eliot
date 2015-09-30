"""
journald support for Eliot.
"""

from cffi import FFI
from os import strerror
from sys import argv
from os.path import basename

from ._bytesjson import dumps
from ._message import TASK_UUID_FIELD, MESSAGE_TYPE_FIELD
from ._action import ACTION_TYPE_FIELD, ACTION_STATUS_FIELD, FAILED_STATUS

_ffi = FFI()
_ffi.cdef("""
int sd_journal_send(const char *format, ...);
""")
try:
    try:
        _journald = _ffi.dlopen("libsystemd.so.0")
    except OSError:
        # Older versions of systemd have separate library:
        _journald = _ffi.dlopen("libsystemd-journal.so.0")
except OSError as e:
    raise ImportError("Failed to load journald: " + str(e))


def sd_journal_send(**kwargs):
    """
    Send a message to the journald log.

    @param kwargs: Mapping between field names to values, both as bytes.

    @raise IOError: If the operation failed.
    """
    # The function uses printf formatting, so we need to quote
    # percentages.
    fields = [_ffi.new("char[]", b"%s=%s" % (key, value.replace(b"%", b"%%")))
              for key, value in kwargs.items()]
    fields.append(_ffi.NULL)
    result = _journald.sd_journal_send(*fields)
    if result != 0:
        raise IOError(-result, strerror(-result))


class JournaldDestination(object):
    """
    A logging destination that writes to journald.

    The message will be logged as JSON, with an additional field
    C{ELIOT_TASK} storing the C{task_uuid} and C{ELIOT_TYPE} storing the
    C{message_type} or C{action_type}.

    Messages for failed actions will get priority 3 ("error"), and
    traceback messages will get priority 2 ("critical"). All other
    messages will get priority 1 ("info").
    """
    def __call__(self, message):
        """
        Write the given message to journald.

        @param message: Dictionary passed from a C{Logger}.
        """
        eliot_type = u""
        priority = b"6"
        if ACTION_TYPE_FIELD in message:
            eliot_type = message[ACTION_TYPE_FIELD]
            if message[ACTION_STATUS_FIELD] == FAILED_STATUS:
                priority = b"3"
        elif MESSAGE_TYPE_FIELD in message:
            eliot_type = message[MESSAGE_TYPE_FIELD]
            if eliot_type == u"eliot:traceback":
                priority = b"2"
        sd_journal_send(MESSAGE=dumps(message),
                        ELIOT_TASK=message[TASK_UUID_FIELD].encode("utf-8"),
                        ELIOT_TYPE=eliot_type.encode("utf-8"),
                        SYSLOG_IDENTIFIER=basename(argv[0]).encode("utf-8"),
                        PRIORITY=priority)
