"""
Implementation of hooks and APIs for outputting log messages.
"""

from __future__ import unicode_literals

from six import text_type as unicode, PY3
if PY3:
    from . import _py3json as json
    pyjson = json
else:
    try:
        # ujson is pretty crappy... but much faster than built-in json module, at
        # least on CPython. So we use it until we come up with some better. We
        # import built-in module for use by the validation code path, since want
        # to validate messages encode in all JSON encoders.
        import ujson as json
        import json as pyjson
    except ImportError:
        import json
        pyjson = json



from zope.interface import Interface, implementer

from ._traceback import writeTraceback, TRACEBACK_MESSAGE
from ._message import Message
from ._util import saferepr


class Destinations(object):
    """
    Manage a list of destinations for message dictionaries.

    The global instance of this class is where L{Logger} instances will
    send written messages.
    """
    def __init__(self):
        self._destinations = []


    def send(self, message):
        """
        Deliver a message to all destinations.

        @param message: A message dictionary that can be serialized to JSON.
        @type serialize: L{bytes}
        """
        for dest in self._destinations:
            try:
                dest(message)
            except:
                # Remember how we said destinations should never raise an
                # exception? That's because we drop them on the floor. You do
                # not want to be here. This is a bad place.
                pass


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


    def write(self, dictionary, serializer=None):
        """
        Serialize the dictionary, and write it to C{self._destinations}.
        """
        dictionary = dictionary.copy()
        try:
            if serializer is not None:
                serializer.serialize(dictionary)
            self._destinations.send(dictionary)
        except:
            writeTraceback(self, "eliot:output")
            msg = Message({"message_type": "eliot:serialization_failure",
                           "message": self._safeUnicodeDictionary(dictionary)})
            msg.write(self)



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
            if isinstance(message["reason"], exceptionType):
                result.append(message)
            else:
                remaining.append(message)
        self.tracebackMessages = remaining
        return result


    def write(self, dictionary, serializer=None):
        """
        Add the dictionary to list of messages.
        """
        self.messages.append(dictionary)
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
            json.dumps(dictionary)
            pyjson.dumps(dictionary)


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
