"""
Implementation of hooks and APIs for outputting log messages.
"""

from __future__ import unicode_literals, absolute_import

import sys
import json as pyjson

from six import text_type as unicode, PY3

from pyrsistent import PClass, field

from . import _bytesjson as slow_json
if PY3:
    fast_json = slow_json
else:
    try:
        # ujson has some issues, in particular it is far too lenient on bad
        # inputs... but on the other hand it's much faster than built-in
        # json module on CPython. So we use it until we come up with some
        # better. We import built-in module for use by the validation code
        # path, since we want to validate messages encode in all JSON
        # encoders.
        import ujson as fast_json
    except ImportError:
        import json as fast_json



from zope.interface import Interface, implementer

from ._traceback import writeTraceback, TRACEBACK_MESSAGE
from ._message import (
    Message,
    EXCEPTION_FIELD,
    MESSAGE_TYPE_FIELD,
    REASON_FIELD,
)
from ._util import saferepr, safeunicode



class _DestinationsSendError(Exception):
    """
    An error occured sending to one or more destinations.

    @ivar errors: A list of tuples output from C{sys.exc_info()}.
    """
    def __init__(self, errors):
        self.errors = errors
        Exception.__init__(self)



class Destinations(object):
    """
    Manage a list of destinations for message dictionaries.

    The global instance of this class is where L{Logger} instances will
    send written messages.
    """
    def __init__(self):
        self._destinations = []
        self._globalFields = {}


    def addGlobalFields(self, **fields):
        """
        Add fields that will be included in all messages sent through this
        destination.

        @param fields: Keyword arguments mapping field names to values.
        """
        self._globalFields.update(fields)


    def send(self, message):
        """
        Deliver a message to all destinations.

        The passed in message might be mutated.

        @param message: A message dictionary that can be serialized to JSON.
        @type message: L{dict}
        """
        message.update(self._globalFields)
        errors = []
        for dest in self._destinations:
            try:
                dest(message)
            except:
                errors.append(sys.exc_info())
        if errors:
            raise _DestinationsSendError(errors)


    def add(self, destination):
        """
        Add a new destination.

        A destination should never ever throw an exception. Seriously.
        A destination should not mutate the dictionary it is given.

        @param destination: A callable that takes message dictionaries,
        """
        self._destinations.append(destination)


    def remove(self, destination):
        """
        Remove an existing destination.

        @param destination: A destination previously added with C{self.add}.

        @raises ValueError: If the destination is unknown.
        """
        self._destinations.remove(destination)



class ILogger(Interface):
    """
    Write out message dictionaries to some destination.
    """
    def bind(**arguments):
        """
		Bind given argument(s) to this logger.

        Every message logged via this logger will include these arguments

        @param **arguments: key/value pairs to bind to this logger
		"""


    def write(dictionary, serializer=None):
        """
        Write a dictionary to the appropriate destination.

        @param serializer: Either C{None}, or a
            L{eliot._validation._MessageSerializer} which can be used to validate
            this message.

        @param dictionary: The message to write out. The given dictionary
             will not be mutated.
        @type dictionary: C{dict}
        """



@implementer(ILogger)
class Logger(object):
    """
    Write out messages to the globally configured destination(s).

    You will typically want to create one of these for every chunk of code
    whose messages you want to unit test in isolation, e.g. a class. The tests
    can then replace a specific L{Logger} with a L{MemoryLogger}.
    """
    _destinations = Destinations()


    def __init__(self):
        self.binded_args = dict()


    def _safeUnicodeDictionary(self, dictionary):
        """
        Serialize a dictionary to a unicode string no matter what it contains.

        The resulting dictionary will loosely follow Python syntax but it is
        not expected to actually be a lossless encoding in all cases.

        @param dictionary: A L{dict} to serialize.

        @return: A L{unicode} string representing the input dictionary as
            faithfully as can be done without putting in too much effort.
        """
        try:
            return unicode(
                dict((saferepr(key), saferepr(value)) for (key, value)
                     in dictionary.items()))
        except:
            return saferepr(dictionary)


    def bind(self, **arguments):
        """
        Bind given arguments to this logger
        """
        self.binded_args.update(arguments)


    def write(self, dictionary, serializer=None):
        """
        Serialize the dictionary, and write it to C{self._destinations}.
        """
        dictionary = dict(self.binded_args, **dictionary.copy())
        try:
            if serializer is not None:
                serializer.serialize(dictionary)
        except:
            writeTraceback(self)
            msg = Message({MESSAGE_TYPE_FIELD: "eliot:serialization_failure",
                           "message": self._safeUnicodeDictionary(dictionary)})
            msg.write(self)
            return

        try:
            self._destinations.send(dictionary)
        except _DestinationsSendError as e:
            for (exc_type, exception, exc_traceback) in e.errors:
                try:
                    # Can't use same code path as serialization errors because
                    # if destination continues to error out we will get
                    # infinite recursion. So instead we have to manually
                    # construct a message.
                    msg = Message({
                        MESSAGE_TYPE_FIELD: "eliot:destination_failure",
                        REASON_FIELD: safeunicode(exception),
                        EXCEPTION_FIELD:
                        exc_type.__module__ + "." + exc_type.__name__,
                        "message": self._safeUnicodeDictionary(dictionary)})
                    self._destinations.send(dict(msg._freeze()))
                except:
                    # Nothing we can do here, raising exception to caller will
                    # break business logic, better to have that continue to
                    # work even if logging isn't.
                    pass


class UnflushedTracebacks(Exception):
    """
    The L{MemoryLogger} had some tracebacks logged which were not flushed.

    This means either your code has a bug and logged an unexpected traceback. If
    you expected the traceback then you will need to flush it using
    L{MemoryLogger.flushTracebacks}.
    """




@implementer(ILogger)
class MemoryLogger(object):
    """
    Store written messages in memory.

    When unit testing you don't want to create this directly but rather use
    the L{eliot.testing.validateLogging} decorator on a test method, which
    will provide additional testing integration.

    @ivar messages: A C{list} of the dictionaries passed to
        L{MemoryLogger.write}. Do not mutate this list.

    @ivar serializers: A C{list} of the serializers passed to
        L{MemoryLogger.write}, each corresponding to a message
        L{MemoryLogger.messages}. Do not mutate this list.

    @ivar tracebackMessages: A C{list} of messages written to this logger for
        tracebacks using L{eliot.writeTraceback} or L{eliot.writeFailure}. Do
        not mutate this list.
    """
    def __init__(self):
        self.reset()
        self.binded_args = dict()


    def flushTracebacks(self, exceptionType):
        """
        Flush all logged tracebacks whose exception is of the given type.

        This means they are expected tracebacks and should not cause the test to
        fail.

        @param exceptionType: A subclass of L{Exception}.

        @return: C{list} of flushed messages.
        """
        result = []
        remaining = []
        for message in self.tracebackMessages:
            if isinstance(message[REASON_FIELD], exceptionType):
                result.append(message)
            else:
                remaining.append(message)
        self.tracebackMessages = remaining
        return result


    # PEP 8 variant:
    flush_tracebacks = flushTracebacks


    def bind(self, **arguments):
        """
        Bind given arguments to this logger
        """
        self.binded_args.update(arguments)


    def write(self, dictionary, serializer=None):
        """
        Add the dictionary to list of messages.
        """
        self.messages.append(dict(self.binded_args, **dictionary))
        self.serializers.append(serializer)
        if serializer is TRACEBACK_MESSAGE._serializer:
            self.tracebackMessages.append(dictionary)


    def validate(self):
        """
        Validate all written messages.

        Does minimal validation of types, and for messages with corresponding
        serializers use those to do additional validation.

        @raises TypeError: If a field name is not unicode.

        @raises eliot.ValidationError: If serializer was given and validation
            failed.
        """
        for dictionary, serializer in zip(self.messages, self.serializers):
            if serializer is not None:
                serializer.validate(dictionary)
            for key in dictionary:
                if not isinstance(key, unicode):
                    if isinstance(key, bytes):
                        key.decode("utf-8")
                    else:
                        raise TypeError(dictionary, "%r is not unicode" % (key,))
            if serializer is not None:
                serializer.serialize(dictionary)

            # Make sure we can be encoded with different JSON encoder, since
            # ujson has different behavior in some cases:
            fast_json.dumps(dictionary)
            slow_json.dumps(dictionary)


    def serialize(self):
        """
        Serialize all written messages.

        This is the Field-based serialization, not JSON.

        @return: A C{list} of C{dict}, the serialized messages.
        """
        result = []
        for dictionary, serializer in zip(self.messages, self.serializers):
            dictionary = dictionary.copy()
            serializer.serialize(dictionary)
            result.append(dictionary)
        return result


    def reset(self):
        """
        Clear all logged messages.

        Any logged tracebacks will also be cleared, and will therefore not cause
        a test failure.

        This is useful to ensure a logger is in a known state before testing
        logging of a specific code path.
        """
        self.messages = []
        self.serializers = []
        self.tracebackMessages = []



class FileDestination(PClass):
    """
    Callable that writes JSON messages to a file.

    On Python 3 the file may support either C{bytes} or C{unicode}.  On
    Python 2 only C{bytes} are supported since that is what all files expect
    in practice.

    @ivar file: The file to which messages will be written.

    @ivar _dumps: Function that serializes an object to JSON.

    @ivar _linebreak: C{"\n"} as either bytes or unicode.
    """
    file = field(mandatory=True)
    _dumps = field(mandatory=True)
    _linebreak = field(mandatory=True)

    def __new__(cls, file):
        unicodeFile = False
        if PY3:
            try:
                file.write(b"")
            except TypeError:
                unicodeFile = True

        if unicodeFile:
            # On Python 3 native json module outputs unicode:
            _dumps = pyjson.dumps
            _linebreak = u"\n"
        else:
            _dumps = fast_json.dumps
            _linebreak = b"\n"
        return PClass.__new__(
            cls, file=file, _dumps=_dumps, _linebreak=_linebreak)

    def __call__(self, message):
        """
        @param message: A message dictionary.
        """
        self.file.write(self._dumps(message) + self._linebreak)
        self.file.flush()


def to_file(output_file):
    """
    Add a destination that writes a JSON message per line to the given file.

    @param output_file: A file-like object.
    """
    Logger._destinations.add(FileDestination(file=output_file))



# The default Logger, used when none is specified:
_DEFAULT_LOGGER = Logger()
