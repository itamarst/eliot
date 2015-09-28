"""
journald support for Eliot.
"""

from cffi import FFI

_ffi = FFI()
_ffi.cdef("""
int sd_journal_send(const char *format, ...);
""")
_journald = _ffi.dlopen("libsystemd-journal.so.0")


def sd_journal_send(**kwargs):
    """
    Send a message to the journald log.

    @param kwargs: Mapping between field names to values.
    """
    # The function uses printf formatting, so we need to quote
    # percentages.
    fields = [b"%s=%s" % (key, value.replace(b"%", b"%%"))
              for key, value in kwargs.items()] + [_ffi.NULL]
    _journald.sd_journal_send(*fields)
    # XXX check return code
