"""
journald support for Eliot.
"""

from cffi import FFI

from ._bytesjson import dumps

_ffi = FFI()
_ffi.cdef("""
int sd_journal_send(const char *format, ...);
""")
_journald = _ffi.dlopen("libsystemd-journal.so.0")


def sd_journal_send(**kwargs):
    """
    Send a message to the journald log.

    @param kwargs: Mapping between field names to values, both as bytes.
    """
    # The function uses printf formatting, so we need to quote
    # percentages.
    fields = [_ffi.new("char[]", b"%s=%s" % (key, value.replace(b"%", b"%%")))
              for key, value in kwargs.items()]
    fields.append(_ffi.NULL)
    _journald.sd_journal_send(*fields)
    # XXX check return code


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
        sd_journal_send(MESSAGE=dumps(message))
