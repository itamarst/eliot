"""
Logging of tracebacks and L{twisted.python.failure.Failure} instances,
as well as common utilities for handling exception logging.
"""

from __future__ import unicode_literals

import types
import traceback
import sys
from warnings import warn

from six import exec_

from ._message import EXCEPTION_FIELD, REASON_FIELD
from ._util import safeunicode
from ._validation import MessageType, Field
from ._errors import _error_extraction

TRACEBACK_MESSAGE = MessageType(
    "eliot:traceback",
    [Field(REASON_FIELD, safeunicode, "The exception's value."),
     Field("traceback", safeunicode, "The traceback."),
     Field(EXCEPTION_FIELD,
           lambda typ: "%s.%s" % (typ.__module__, typ.__name__),
           "The exception type's FQPN.")],
    "An unexpected exception indicating a bug.")
# The fields here are actually subset of what you might get in practice,
# due to exception extraction, so we hackily modify the serializer:
TRACEBACK_MESSAGE._serializer.allow_additional_fields = True


def _writeTracebackMessage(logger, typ, exception, traceback):
    """
    Write a traceback to the log.

    @param typ: The class of the exception.

    @param exception: The L{Exception} instance.

    @param traceback: The traceback, a C{str}.
    """
    msg = TRACEBACK_MESSAGE(reason=exception, traceback=traceback,
                            exception=typ)
    msg = msg.bind(**_error_extraction.get_fields_for_exception(
        logger, exception))
    msg.write(logger)


# The default Python standard library traceback.py formatting functions
# involving reading source from disk. This is a potential performance hit
# since disk I/O can block. We therefore format the tracebacks with in-memory
# information only.
#
# Unfortunately, the easiest way to do this is... exciting.
def _get_traceback_no_io():
    """
    Return a version of L{traceback} that doesn't do I/O.
    """
    module = types.ModuleType(str("_traceback_no_io"))
    path = traceback.__file__
    if path.endswith(".pyc") or path.endswith(".pyo"):
        path = path[:-1]
    with open(path) as f:
        exec_(f.read(), module.__dict__, module.__dict__)
    class FakeLineCache(object):
        def checkcache(self, *args, **kwargs):
            None
        def getline(self, *args, **kwargs):
            return ""
        def lazycache(self, *args, **kwargs):
            return None
    module.linecache = FakeLineCache()
    return module
_traceback_no_io = _get_traceback_no_io()


def writeTraceback(logger=None, system=None):
    """
    Write the latest traceback to the log.

    This should be used inside an C{except} block. For example:

         try:
             dostuff()
         except:
             writeTraceback(logger)
    """
    if system is not None:
        warn("The `system` argument to writeTraceback is no longer used.",
             DeprecationWarning, stacklevel=2)

    typ, exception, tb = sys.exc_info()
    traceback = "".join(_traceback_no_io.format_exception(typ, exception, tb))
    _writeTracebackMessage(logger, typ, exception, traceback)



def writeFailure(failure, logger=None, system=None):
    """
    Write a L{twisted.python.failure.Failure} to the log.

    This is for situations where you got an unexpected exception and want to
    log a traceback. For example:

        d = dostuff()
        d.addCallback(process)
        # Final error handler.
        d.addErrback(writeFailure, logger, "myapp:subsystem")

    @param failure: L{Failure} to write to the log.

    @type logger: L{eliot.ILogger}

    @return: None
    """
    if system is not None:
        warn("The `system` argument to writeFailure is no longer used.",
             DeprecationWarning, stacklevel=2)

    # Failure.getBriefTraceback does not include source code, so does not do
    # I/O.
    _writeTracebackMessage(logger, failure.value.__class__,
                           failure.value, failure.getBriefTraceback())
