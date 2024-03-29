"""
Implementation of hooks and APIs for outputting log messages.
"""

import traceback
import inspect
from threading import Lock
from functools import wraps
from io import IOBase
import warnings

from pyrsistent import PClass, field

from zope.interface import Interface, implementer

from ._traceback import write_traceback, TRACEBACK_MESSAGE
from ._message import EXCEPTION_FIELD, MESSAGE_TYPE_FIELD, REASON_FIELD
from ._util import saferepr, safeunicode
from .json import (
    json_default,
    _encoder_to_default_function,
    _dumps_bytes,
    _dumps_unicode,
)
from ._validation import ValidationError


# Action type for log messages due to a (hopefully temporarily) broken
# destination.
DESTINATION_FAILURE = "eliot:destination_failure"


class BufferingDestination(object):
    """
    Buffer messages in memory.
    """

    def __init__(self):
        self.messages = []

    def __call__(self, message):
        self.messages.append(message)
        while len(self.messages) > 1000:
            self.messages.pop(0)


class Destinations(object):
    """
    Manage a list of destinations for message dictionaries.

    The global instance of this class is where L{Logger} instances will
    send written messages.
    """

    def __init__(self):
        self._destinations = [BufferingDestination()]
        self._any_added = False
        self._globalFields = {}

    def addGlobalFields(self, **fields):
        """
        Add fields that will be included in all messages sent through this
        destination.

        @param fields: Keyword arguments mapping field names to values.
        """
        self._globalFields.update(fields)

    def send(self, message, logger=None):
        """
        Deliver a message to all destinations.

        The passed in message might be mutated.

        This should never raise an exception.

        @param message: A message dictionary that can be serialized to JSON.
        @type message: L{dict}

        @param logger: The ``ILogger`` that wrote the message, if any.
        """
        message.update(self._globalFields)
        errors = []
        is_destination_error_message = (
            message.get("message_type", None) == DESTINATION_FAILURE
        )
        for dest in self._destinations:
            try:
                dest(message)
            except Exception as e:
                # If the destination is broken not because of a specific
                # message, but rather continously, we will get a
                # "eliot:destination_failure" log message logged, and so we
                # want to ensure it doesn't do infinite recursion.
                if not is_destination_error_message:
                    errors.append(e)

        for exception in errors:
            from ._action import log_message

            try:
                new_msg = {
                    MESSAGE_TYPE_FIELD: DESTINATION_FAILURE,
                    REASON_FIELD: safeunicode(exception),
                    EXCEPTION_FIELD: exception.__class__.__module__
                    + "."
                    + exception.__class__.__name__,
                    "message": _safe_unicode_dictionary(message),
                }
                if logger is not None:
                    # This is really only useful for testing, should really
                    # figure out way to get rid of this mechanism...
                    new_msg["__eliot_logger__"] = logger
                log_message(**new_msg)
            except:
                # Nothing we can do here, raising exception to caller will
                # break business logic, better to have that continue to
                # work even if logging isn't.
                pass

    def add(self, *destinations):
        """
        Adds new destinations.

        A destination should never ever throw an exception. Seriously.
        A destination should not mutate the dictionary it is given.

        @param destinations: A list of callables that takes message
            dictionaries.
        """
        buffered_messages = None
        if not self._any_added:
            # These are first set of messages added, so we need to clear
            # BufferingDestination:
            self._any_added = True
            buffered_messages = self._destinations[0].messages
            self._destinations = []
        self._destinations.extend(destinations)
        if buffered_messages:
            # Re-deliver buffered messages:
            for message in buffered_messages:
                self.send(message)

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

    def write(dictionary, serializer=None):
        """
        Write a dictionary to the appropriate destination.

        @note: This method is thread-safe.

        @param serializer: Either C{None}, or a
            L{eliot._validation._MessageSerializer} which can be used to
            validate this message.

        @param dictionary: The message to write out. The given dictionary
             will not be mutated.
        @type dictionary: C{dict}
        """


def _safe_unicode_dictionary(dictionary):
    """
    Serialize a dictionary to a unicode string no matter what it contains.

    The resulting dictionary will loosely follow Python syntax but it is
    not expected to actually be a lossless encoding in all cases.

    @param dictionary: A L{dict} to serialize.

    @return: A L{str} string representing the input dictionary as
        faithfully as can be done without putting in too much effort.
    """
    try:
        return str(
            dict(
                (saferepr(key), saferepr(value)) for (key, value) in dictionary.items()
            )
        )
    except:
        return saferepr(dictionary)


@implementer(ILogger)
class Logger(object):
    """
    Write out messages to the globally configured destination(s).

    You will typically want to create one of these for every chunk of code
    whose messages you want to unit test in isolation, e.g. a class. The tests
    can then replace a specific L{Logger} with a L{MemoryLogger}.
    """

    _destinations = Destinations()

    def write(self, dictionary, serializer=None):
        """
        Serialize the dictionary, and write it to C{self._destinations}.
        """
        dictionary = dictionary.copy()
        try:
            if serializer is not None:
                serializer.serialize(dictionary)
        except:
            write_traceback(self)
            from ._action import log_message

            log_message(
                "eliot:serialization_failure",
                message=_safe_unicode_dictionary(dictionary),
                __eliot_logger__=self,
            )
            return

        self._destinations.send(dictionary, self)


def exclusively(f):
    """
    Decorate a function to make it thread-safe by serializing invocations
    using a per-instance lock.
    """

    @wraps(f)
    def exclusively_f(self, *a, **kw):
        with self._lock:
            return f(self, *a, **kw)

    return exclusively_f


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
        tracebacks using L{eliot.write_traceback} or L{eliot.writeFailure}. Do
        not mutate this list.
    """

    def __init__(self, encoder=None, json_default=json_default):
        """
        @param encoder: DEPRECATED.  A JSONEncoder subclass to use when
            encoding JSON.

        @param json_default: A callable that handles objects the default JSON
            serializer can't handle.
        """
        json_default = _json_default_from_encoder_and_json_default(
            encoder, json_default
        )
        self._lock = Lock()
        self._json_default = json_default
        self.reset()

    @exclusively
    def flushTracebacks(self, exceptionType):
        """
        Flush all logged tracebacks whose exception is of the given type.

        This means they are expected tracebacks and should not cause the test
        to fail.

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

    @exclusively
    def write(self, dictionary, serializer=None):
        """
        Add the dictionary to list of messages.
        """
        # Validate copy of the dictionary, to ensure what we store isn't
        # mutated.
        try:
            self._validate_message(dictionary.copy(), serializer)
        except Exception as e:
            # Skip irrelevant frames that don't help pinpoint the problem:
            from . import _output, _message, _action

            skip_filenames = [_output.__file__, _message.__file__, _action.__file__]
            for frame in inspect.stack():
                if frame[1] not in skip_filenames:
                    break
            self._failed_validations.append(
                "{}: {}".format(e, "".join(traceback.format_stack(frame[0])))
            )
        self.messages.append(dictionary)
        self.serializers.append(serializer)
        if serializer is TRACEBACK_MESSAGE._serializer:
            self.tracebackMessages.append(dictionary)

    def _validate_message(self, dictionary, serializer):
        """Validate an individual message.

        As a side-effect, the message is replaced with its serialized contents.

        @param dictionary: A message C{dict} to be validated.  Might be mutated
            by the serializer!

        @param serializer: C{None} or a serializer.

        @raises TypeError: If a field name is not unicode, or the dictionary
            fails to serialize to JSON.

        @raises eliot.ValidationError: If serializer was given and validation
            failed.
        """
        if serializer is not None:
            serializer.validate(dictionary)
        for key in dictionary:
            if not isinstance(key, str):
                if isinstance(key, bytes):
                    key.decode("utf-8")
                else:
                    raise TypeError(dictionary, "%r is not unicode" % (key,))
        if serializer is not None:
            serializer.serialize(dictionary)

        try:
            _dumps_unicode(dictionary, default=self._json_default)
        except Exception as e:
            raise TypeError("Message %s doesn't encode to JSON: %s" % (dictionary, e))

    @exclusively
    def validate(self):
        """
        Validate all written messages.

        Does minimal validation of types, and for messages with corresponding
        serializers use those to do additional validation.

        As a side-effect, the messages are replaced with their serialized
        contents.

        @raises TypeError: If a field name is not unicode, or the dictionary
            fails to serialize to JSON.

        @raises eliot.ValidationError: If serializer was given and validation
            failed.
        """
        for dictionary, serializer in zip(self.messages, self.serializers):
            try:
                self._validate_message(dictionary, serializer)
            except (TypeError, ValidationError) as e:
                # We already figured out which messages failed validation
                # earlier. This just lets us figure out which exception type to
                # raise.
                raise e.__class__("\n\n".join(self._failed_validations))

    @exclusively
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

    @exclusively
    def reset(self):
        """
        Clear all logged messages.

        Any logged tracebacks will also be cleared, and will therefore not
        cause a test failure.

        This is useful to ensure a logger is in a known state before testing
        logging of a specific code path.
        """
        self.messages = []
        self.serializers = []
        self.tracebackMessages = []
        self._failed_validations = []


def _json_default_from_encoder_and_json_default(encoder, json_default):
    if encoder is not None:
        warnings.warn(
            "Using a JSON encoder subclass is no longer supported, please switch to using a default function",
            DeprecationWarning,
            stacklevel=3,
        )
        from .json import json_default as default_json_default

        if json_default is not default_json_default:
            raise RuntimeError("Can't pass in both encoder and default function")

        json_default = _encoder_to_default_function(encoder())
    return json_default


class FileDestination(PClass):
    """
    Callable that writes JSON messages to a file that accepts either C{bytes}
    or C{str}.

    @ivar file: The file to which messages will be written.

    @ivar _dumps: Function that serializes an object to JSON.

    @ivar _linebreak: C{"\n"} as either bytes or unicode.
    """

    file = field(mandatory=True)
    _json_default = field(mandatory=True)
    _dumps = field(mandatory=True)
    _linebreak = field(mandatory=True)

    def __new__(cls, file, encoder=None, json_default=json_default):
        """
        Use ``json_default`` to pass in a default function for JSON dumping.

        The ``encoder`` parameter is deprecated.
        """
        if isinstance(file, IOBase) and not file.writable():
            raise RuntimeError("Given file {} is not writeable.")

        json_default = _json_default_from_encoder_and_json_default(
            encoder, json_default
        )

        unicodeFile = False
        try:
            file.write(b"")
        except TypeError:
            unicodeFile = True

        if unicodeFile:
            _dumps = _dumps_unicode
            _linebreak = "\n"
        else:
            _dumps = _dumps_bytes
            _linebreak = b"\n"
        return PClass.__new__(
            cls,
            file=file,
            _dumps=_dumps,
            _linebreak=_linebreak,
            _json_default=json_default,
        )

    def __call__(self, message):
        """
        @param message: A message dictionary.
        """
        self.file.write(
            self._dumps(message, default=self._json_default) + self._linebreak
        )
        self.file.flush()


def to_file(output_file, encoder=None, json_default=json_default):
    """
    Add a destination that writes a JSON message per line to the given file.

    @param output_file: A file-like object.

    @param encoder: DEPRECATED.  A JSONEncoder subclass to use when encoding
        JSON.

    @param json_default: A callable that handles objects the default JSON
        serializer can't handle.
    """
    Logger._destinations.add(
        FileDestination(file=output_file, encoder=encoder, json_default=json_default)
    )


# The default Logger, used when none is specified:
_DEFAULT_LOGGER = Logger()
