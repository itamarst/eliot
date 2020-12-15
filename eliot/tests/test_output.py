"""
Tests for L{eliot._output}.
"""

from sys import stdout
from unittest import TestCase, skipUnless

# Make sure to use StringIO that only accepts unicode:
from io import BytesIO, StringIO
import json as pyjson
from tempfile import mktemp
from time import time
from uuid import UUID
from threading import Thread

try:
    import numpy as np
except ImportError:
    np = None
from zope.interface.verify import verifyClass

from .._output import (
    MemoryLogger,
    ILogger,
    Destinations,
    Logger,
    bytesjson as json,
    to_file,
    FileDestination,
    _DestinationsSendError,
)
from .._validation import ValidationError, Field, _MessageSerializer
from .._traceback import write_traceback
from ..testing import assertContainsFields
from .common import CustomObject, CustomJSONEncoder


class MemoryLoggerTests(TestCase):
    """
    Tests for L{MemoryLogger}.
    """

    def test_interface(self):
        """
        L{MemoryLogger} implements L{ILogger}.
        """
        verifyClass(ILogger, MemoryLogger)

    def test_write(self):
        """
        Dictionaries written with L{MemoryLogger.write} are stored on a list.
        """
        logger = MemoryLogger()
        logger.write({"a": "b"})
        logger.write({"c": 1})
        self.assertEqual(logger.messages, [{"a": "b"}, {"c": 1}])
        logger.validate()

    def test_notStringFieldKeys(self):
        """
        Field keys must be unicode or bytes; if not L{MemoryLogger.validate}
        raises a C{TypeError}.
        """
        logger = MemoryLogger()
        logger.write({123: "b"})
        self.assertRaises(TypeError, logger.validate)

    def test_bytesMustBeUTF8(self):
        """
        Field keys can be bytes, but only if they're UTF-8 encoded Unicode.
        """
        logger = MemoryLogger()
        logger.write({"\u1234".encode("utf-16"): "b"})
        self.assertRaises(UnicodeDecodeError, logger.validate)

    def test_serializer(self):
        """
        L{MemoryLogger.validate} calls the given serializer's C{validate()}
        method with the message, as does L{MemoryLogger.write}.
        """

        class FakeValidator(list):
            def validate(self, message):
                self.append(message)

            def serialize(self, obj):
                return obj

        validator = FakeValidator()
        logger = MemoryLogger()
        message = {"message_type": "mymessage", "X": 1}
        logger.write(message, validator)
        self.assertEqual(validator, [message])
        logger.validate()
        self.assertEqual(validator, [message, message])

    def test_failedValidation(self):
        """
        L{MemoryLogger.validate} will allow exceptions raised by the serializer
        to pass through.
        """
        serializer = _MessageSerializer(
            [Field.forValue("message_type", "mymessage", "The type")]
        )
        logger = MemoryLogger()
        logger.write({"message_type": "wrongtype"}, serializer)
        self.assertRaises(ValidationError, logger.validate)

    def test_JSON(self):
        """
        L{MemoryLogger.validate} will encode the output of serialization to
        JSON.
        """
        serializer = _MessageSerializer(
            [
                Field.forValue("message_type", "type", "The type"),
                Field("foo", lambda value: object(), "The type"),
            ]
        )
        logger = MemoryLogger()
        logger.write(
            {"message_type": "type", "foo": "will become object()"}, serializer
        )
        self.assertRaises(TypeError, logger.validate)

    @skipUnless(np, "NumPy is not installed.")
    def test_EliotJSONEncoder(self):
        """
        L{MemoryLogger.validate} uses the EliotJSONEncoder by default to do
        encoding testing.
        """
        logger = MemoryLogger()
        logger.write({"message_type": "type", "foo": np.uint64(12)}, None)
        logger.validate()

    def test_JSON_custom_encoder(self):
        """
        L{MemoryLogger.validate} will use a custom JSON encoder if one was given.
        """
        logger = MemoryLogger(encoder=CustomJSONEncoder)
        logger.write(
            {"message_type": "type", "custom": CustomObject()},
            None,
        )
        logger.validate()

    def test_serialize(self):
        """
        L{MemoryLogger.serialize} returns a list of serialized versions of the
        logged messages.
        """
        serializer = _MessageSerializer(
            [
                Field.forValue("message_type", "mymessage", "The type"),
                Field("length", len, "The length"),
            ]
        )
        messages = [
            {"message_type": "mymessage", "length": "abc"},
            {"message_type": "mymessage", "length": "abcd"},
        ]
        logger = MemoryLogger()
        for message in messages:
            logger.write(message, serializer)
        self.assertEqual(
            logger.serialize(),
            [
                {"message_type": "mymessage", "length": 3},
                {"message_type": "mymessage", "length": 4},
            ],
        )

    def test_serializeCopies(self):
        """
        L{MemoryLogger.serialize} does not mutate the original logged messages.
        """
        serializer = _MessageSerializer(
            [
                Field.forValue("message_type", "mymessage", "The type"),
                Field("length", len, "The length"),
            ]
        )
        message = {"message_type": "mymessage", "length": "abc"}
        logger = MemoryLogger()
        logger.write(message, serializer)
        logger.serialize()
        self.assertEqual(logger.messages[0]["length"], "abc")

    def write_traceback(self, logger, exception):
        """
        Write an exception as a traceback to the logger.
        """
        try:
            raise exception
        except:
            write_traceback(logger)

    def test_tracebacksCauseTestFailure(self):
        """
        Logging a traceback to L{MemoryLogger} will add its exception to
        L{MemoryLogger.tracebackMessages}.
        """
        logger = MemoryLogger()
        exception = Exception()
        self.write_traceback(logger, exception)
        self.assertEqual(logger.tracebackMessages[0]["reason"], exception)

    def test_flushTracebacksNoTestFailure(self):
        """
        Any tracebacks cleared by L{MemoryLogger.flushTracebacks} (as specified
        by exception type) are removed from
        L{MemoryLogger.tracebackMessages}.
        """
        logger = MemoryLogger()
        exception = RuntimeError()
        self.write_traceback(logger, exception)
        logger.flushTracebacks(RuntimeError)
        self.assertEqual(logger.tracebackMessages, [])

    def test_flushTracebacksReturnsExceptions(self):
        """
        L{MemoryLogger.flushTracebacks} returns the traceback messages.
        """
        exceptions = [ZeroDivisionError(), ZeroDivisionError()]
        logger = MemoryLogger()
        logger.write({"x": 1})
        for exc in exceptions:
            self.write_traceback(logger, exc)
        logger.write({"x": 1})
        flushed = logger.flushTracebacks(ZeroDivisionError)
        self.assertEqual(flushed, logger.messages[1:3])

    def test_flushTracebacksUnflushedTestFailure(self):
        """
        Any tracebacks uncleared by L{MemoryLogger.flushTracebacks} (because
        they are of a different type) are still listed in
        L{MemoryLogger.tracebackMessages}.
        """
        logger = MemoryLogger()
        exception = RuntimeError()
        self.write_traceback(logger, exception)
        logger.flushTracebacks(KeyError)
        self.assertEqual(logger.tracebackMessages[0]["reason"], exception)

    def test_flushTracebacksUnflushedUnreturned(self):
        """
        Any tracebacks uncleared by L{MemoryLogger.flushTracebacks} (because
        they are of a different type) are not returned.
        """
        logger = MemoryLogger()
        exception = RuntimeError()
        self.write_traceback(logger, exception)
        self.assertEqual(logger.flushTracebacks(KeyError), [])

    def test_reset(self):
        """
        L{MemoryLogger.reset} clears all logged messages and tracebacks.
        """
        logger = MemoryLogger()
        logger.write({"key": "value"}, None)
        logger.reset()
        self.assertEqual(
            (logger.messages, logger.serializers, logger.tracebackMessages),
            ([], [], []),
        )

    def test_threadSafeWrite(self):
        """
        L{MemoryLogger.write} can be called from multiple threads concurrently.
        """
        # Some threads will log some messages
        thread_count = 10

        # A lot of messages.  This will keep the threads running long enough
        # to give them a chance to (try to) interfere with each other.
        write_count = 10000

        # They'll all use the same MemoryLogger instance.
        logger = MemoryLogger()

        # Each thread will have its own message and serializer that it writes
        # to the log over and over again.
        def write(msg, serializer):
            for i in range(write_count):
                logger.write(msg, serializer)

        # Generate a single distinct message for each thread to log.
        msgs = list({"i": i} for i in range(thread_count))

        # Generate a single distinct serializer for each thread to log.
        serializers = list(object() for i in range(thread_count))

        # Pair them all up.  This gives us a simple invariant we can check
        # later on.
        write_args = zip(msgs, serializers)

        # Create the threads.
        threads = list(Thread(target=write, args=args) for args in write_args)

        # Run them all.  Note threads early in this list will start writing to
        # the log before later threads in the list even get a chance to start.
        # That's part of why we have each thread write so many messages.
        for t in threads:
            t.start()
        # Wait for them all to finish.
        for t in threads:
            t.join()

        # Check that we got the correct number of messages in the log.
        expected_count = thread_count * write_count
        self.assertEqual(len(logger.messages), expected_count)
        self.assertEqual(len(logger.serializers), expected_count)

        # Check the simple invariant we created above.  Every logged message
        # must be paired with the correct serializer, where "correct" is
        # defined by ``write_args`` above.
        for position, (msg, serializer) in enumerate(
            zip(logger.messages, logger.serializers)
        ):
            # The indexes must match because the objects are paired using
            # zip() above.
            msg_index = msgs.index(msg)
            serializer_index = serializers.index(serializer)
            self.assertEqual(
                msg_index,
                serializer_index,
                "Found message #{} with serializer #{} at position {}".format(
                    msg_index, serializer_index, position
                ),
            )


class MyException(Exception):
    """
    Custom exception.
    """


class BadDestination(list):
    """
    A destination that throws an exception the first time it is called.
    """

    called = 0

    def __call__(self, msg):
        if not self.called:
            self.called = True
            raise MyException("ono")
        self.append(msg)


class DestinationsTests(TestCase):
    """
    Tests for L{Destinations}.
    """

    def test_send(self):
        """
        L{Destinations.send} calls all destinations added with
        L{Destinations.add} with the given dictionary.
        """
        destinations = Destinations()
        message = {"hoorj": "blargh"}
        dest = []
        dest2 = []
        dest3 = []
        destinations.add(dest.append, dest2.append)
        destinations.add(dest3.append)
        destinations.send(message)
        self.assertEqual(dest, [message])
        self.assertEqual(dest2, [message])
        self.assertEqual(dest3, [message])

    def test_destinationExceptionMultipleDestinations(self):
        """
        If one destination throws an exception, other destinations still
        get the message.
        """
        destinations = Destinations()
        dest = []
        dest2 = BadDestination()
        dest3 = []
        destinations.add(dest.append)
        destinations.add(dest2)
        destinations.add(dest3.append)

        message = {"hello": 123}
        self.assertRaises(_DestinationsSendError, destinations.send, {"hello": 123})
        self.assertEqual((dest, dest3), ([message], [message]))

    def test_destinationExceptionContinue(self):
        """
        If a destination throws an exception, future messages are still
        sent to it.
        """
        destinations = Destinations()
        dest = BadDestination()
        destinations.add(dest)

        self.assertRaises(_DestinationsSendError, destinations.send, {"hello": 123})
        destinations.send({"hello": 200})
        self.assertEqual(dest, [{"hello": 200}])

    def test_remove(self):
        """
        A destination removed with L{Destinations.remove} will no longer
        receive messages from L{Destionations.add} calls.
        """
        destinations = Destinations()
        message = {"hello": 123}
        dest = []
        destinations.add(dest.append)
        destinations.remove(dest.append)
        destinations.send(message)
        self.assertEqual(dest, [])

    def test_removeNonExistent(self):
        """
        Removing a destination that has not previously been added with result
        in a C{ValueError} being thrown.
        """
        destinations = Destinations()
        self.assertRaises(ValueError, destinations.remove, [].append)

    def test_addGlobalFields(self):
        """
        L{Destinations.addGlobalFields} adds the given fields and values to
        the messages being passed in.
        """
        destinations = Destinations()
        dest = []
        destinations.add(dest.append)
        destinations.addGlobalFields(x=123, y="hello")
        destinations.send({"z": 456})
        self.assertEqual(dest, [{"x": 123, "y": "hello", "z": 456}])

    def test_addGlobalFieldsCumulative(self):
        """
        L{Destinations.addGlobalFields} adds the given fields to those set by
        previous calls.
        """
        destinations = Destinations()
        dest = []
        destinations.add(dest.append)
        destinations.addGlobalFields(x=123, y="hello")
        destinations.addGlobalFields(x=456, z=456)
        destinations.send({"msg": "X"})
        self.assertEqual(dest, [{"x": 456, "y": "hello", "z": 456, "msg": "X"}])

    def test_buffering(self):
        """
        Before any destinations are set up to 1000 messages are buffered, and
        then delivered to the first registered destinations.
        """
        destinations = Destinations()
        messages = [{"k": i} for i in range(1050)]
        for m in messages:
            destinations.send(m)
        dest, dest2 = [], []
        destinations.add(dest.append, dest2.append)
        self.assertEqual((dest, dest2), (messages[-1000:], messages[-1000:]))

    def test_buffering_second_batch(self):
        """
        The second batch of added destination don't get the buffered messages.
        """
        destinations = Destinations()
        message = {"m": 1}
        message2 = {"m": 2}
        destinations.send(message)
        dest = []
        dest2 = []
        destinations.add(dest.append)
        destinations.add(dest2.append)
        destinations.send(message2)
        self.assertEqual((dest, dest2), ([message, message2], [message2]))

    def test_global_fields_buffering(self):
        """
        Global fields are added to buffered messages, when possible.
        """
        destinations = Destinations()
        message = {"m": 1}
        destinations.send(message)
        destinations.addGlobalFields(k=123)
        dest = []
        destinations.add(dest.append)
        self.assertEqual(dest, [{"m": 1, "k": 123}])


def makeLogger():
    """
    Return a tuple (L{Logger} instance, C{list} of written messages).
    """
    logger = Logger()
    logger._destinations = Destinations()
    written = []
    logger._destinations.add(written.append)
    return logger, written


class LoggerTests(TestCase):
    """
    Tests for L{Logger}.
    """

    def test_interface(self):
        """
        L{Logger} implements L{ILogger}.
        """
        verifyClass(ILogger, Logger)

    def test_global(self):
        """
        A global L{Destinations} is used by the L{Logger} class.
        """
        self.assertIsInstance(Logger._destinations, Destinations)

    def test_write(self):
        """
        L{Logger.write} sends the given dictionary L{Destinations} object.
        """
        logger, written = makeLogger()

        d = {"hello": 1}
        logger.write(d)
        self.assertEqual(written, [d])

    def test_serializer(self):
        """
        If a L{_MessageSerializer} is passed to L{Logger.write}, it is used to
        serialize the message before it is passed to the destination.
        """
        logger, written = makeLogger()

        serializer = _MessageSerializer(
            [
                Field.forValue("message_type", "mymessage", "The type"),
                Field("length", len, "The length of a thing"),
            ]
        )
        logger.write({"message_type": "mymessage", "length": "thething"}, serializer)
        self.assertEqual(written, [{"message_type": "mymessage", "length": 8}])

    def test_passedInDictionaryUnmodified(self):
        """
        The dictionary passed in to L{Logger.write} is not modified.
        """
        logger, written = makeLogger()

        serializer = _MessageSerializer(
            [
                Field.forValue("message_type", "mymessage", "The type"),
                Field("length", len, "The length of a thing"),
            ]
        )
        d = {"message_type": "mymessage", "length": "thething"}
        original = d.copy()
        logger.write(d, serializer)
        self.assertEqual(d, original)

    def test_safeUnicodeDictionary(self):
        """
        L{Logger._safeUnicodeDictionary} converts the given dictionary's
        values and keys to unicode using C{safeunicode}.
        """

        class badobject(object):
            def __repr__(self):
                raise TypeError()

        dictionary = {badobject(): 123, 123: badobject()}
        badMessage = "eliot: unknown, unicode() raised exception"
        self.assertEqual(
            eval(Logger()._safeUnicodeDictionary(dictionary)),
            {badMessage: "123", "123": badMessage},
        )

    def test_safeUnicodeDictionaryFallback(self):
        """
        If converting the dictionary failed for some reason,
        L{Logger._safeUnicodeDictionary} runs C{repr} on the object.
        """
        self.assertEqual(Logger()._safeUnicodeDictionary(None), "None")

    def test_safeUnicodeDictionaryFallbackFailure(self):
        """
        If all else fails, L{Logger._safeUnicodeDictionary} just gives up.
        """

        class badobject(object):
            def __repr__(self):
                raise TypeError()

        self.assertEqual(
            Logger()._safeUnicodeDictionary(badobject()),
            "eliot: unknown, unicode() raised exception",
        )

    def test_serializationErrorTraceback(self):
        """
        If serialization fails in L{Logger.write}, a traceback is logged,
        along with a C{eliot:serialization_failure} message for debugging
        purposes.
        """
        logger, written = makeLogger()

        def raiser(i):
            raise RuntimeError("oops")

        serializer = _MessageSerializer(
            [
                Field.forValue("message_type", "mymessage", "The type"),
                Field("fail", raiser, "Serialization fail"),
            ]
        )
        message = {"message_type": "mymessage", "fail": "will"}
        logger.write(message, serializer)
        self.assertEqual(len(written), 2)
        tracebackMessage = written[0]
        assertContainsFields(
            self,
            tracebackMessage,
            {
                "exception": "%s.RuntimeError" % (RuntimeError.__module__,),
                "message_type": "eliot:traceback",
            },
        )
        self.assertIn("RuntimeError: oops", tracebackMessage["traceback"])
        # Calling _safeUnicodeDictionary multiple times leads to
        # inconsistent results due to hash ordering, so compare contents:
        assertContainsFields(
            self, written[1], {"message_type": "eliot:serialization_failure"}
        )
        self.assertEqual(
            eval(written[1]["message"]),
            dict((repr(key), repr(value)) for (key, value) in message.items()),
        )

    def test_destinationExceptionCaught(self):
        """
        If a destination throws an exception, an appropriate error is
        logged.
        """
        logger = Logger()
        logger._destinations = Destinations()
        dest = BadDestination()
        logger._destinations.add(dest)

        message = {"hello": 123}
        logger.write({"hello": 123})
        assertContainsFields(
            self,
            dest[0],
            {
                "message_type": "eliot:destination_failure",
                "message": logger._safeUnicodeDictionary(message),
                "reason": "ono",
                "exception": "eliot.tests.test_output.MyException",
            },
        )

    def test_destinationMultipleExceptionsCaught(self):
        """
        If multiple destinations throw an exception, an appropriate error is
        logged for each.
        """
        logger = Logger()
        logger._destinations = Destinations()
        logger._destinations.add(BadDestination())
        logger._destinations.add(lambda msg: 1 / 0)
        messages = []
        logger._destinations.add(messages.append)

        try:
            1 / 0
        except ZeroDivisionError as e:
            zero_divide = str(e)
        zero_type = ZeroDivisionError.__module__ + ".ZeroDivisionError"

        message = {"hello": 123}
        logger.write({"hello": 123})

        def remove(key):
            return [message.pop(key) for message in messages[1:]]

        # Make sure we have task_level & task_uuid in exception messages.
        task_levels = remove("task_level")
        task_uuids = remove("task_uuid")
        timestamps = remove("timestamp")

        self.assertEqual(
            (
                abs(timestamps[0] + timestamps[1] - 2 * time()) < 1,
                task_levels == [[1], [1]],
                len([UUID(uuid) for uuid in task_uuids]) == 2,
                messages,
            ),
            (
                True,
                True,
                True,
                [
                    message,
                    {
                        "message_type": "eliot:destination_failure",
                        "message": logger._safeUnicodeDictionary(message),
                        "reason": "ono",
                        "exception": "eliot.tests.test_output.MyException",
                    },
                    {
                        "message_type": "eliot:destination_failure",
                        "message": logger._safeUnicodeDictionary(message),
                        "reason": zero_divide,
                        "exception": zero_type,
                    },
                ],
            ),
        )

    def test_destinationExceptionCaughtTwice(self):
        """
        If a destination throws an exception, and the logged error about
        it also causes an exception, then just drop that exception on the
        floor, since there's nothing we can do with it.
        """
        logger = Logger()
        logger._destinations = Destinations()

        def always_raise(message):
            raise ZeroDivisionError()

        logger._destinations.add(always_raise)

        # No exception raised; since everything is dropped no other
        # assertions to be made.
        logger.write({"hello": 123})


class PEP8Tests(TestCase):
    """
    Tests for PEP 8 method compatibility.
    """

    def test_flush_tracebacks(self):
        """
        L{MemoryLogger.flush_tracebacks} is the same as
        L{MemoryLogger.flushTracebacks}
        """
        self.assertEqual(MemoryLogger.flush_tracebacks, MemoryLogger.flushTracebacks)


class ToFileTests(TestCase):
    """
    Tests for L{to_file}.
    """

    def test_to_file_adds_destination(self):
        """
        L{to_file} adds a L{FileDestination} destination with the given file.
        """
        f = stdout
        to_file(f)
        expected = FileDestination(file=f)
        self.addCleanup(Logger._destinations.remove, expected)
        self.assertIn(expected, Logger._destinations._destinations)

    def test_to_file_custom_encoder(self):
        """
        L{to_file} accepts a custom encoder, and sets it on the resulting
        L{FileDestination}.
        """
        f = stdout
        encoder = object()
        to_file(f, encoder=encoder)
        expected = FileDestination(file=f, encoder=encoder)
        self.addCleanup(Logger._destinations.remove, expected)
        self.assertIn(expected, Logger._destinations._destinations)

    def test_bytes_values(self):
        """
        DEPRECATED: On Python 3L{FileDestination} will encode bytes as if they were
        UTF-8 encoded strings when writing to BytesIO only.
        """
        message = {"x": b"abc"}
        bytes_f = BytesIO()
        destination = FileDestination(file=bytes_f)
        destination(message)
        self.assertEqual(
            [json.loads(line) for line in bytes_f.getvalue().splitlines()],
            [{"x": "abc"}],
        )

    @skipUnless(np, "NumPy is not installed.")
    def test_default_encoder_is_EliotJSONEncoder(self):
        """The default encoder if none are specified is EliotJSONEncoder."""
        message = {"x": np.int64(3)}
        f = StringIO()
        destination = FileDestination(file=f)
        destination(message)
        self.assertEqual(
            [json.loads(line) for line in f.getvalue().splitlines()], [{"x": 3}]
        )

    def test_filedestination_writes_json_bytes(self):
        """
        L{FileDestination} writes JSON-encoded messages to a file that accepts
        bytes.
        """
        message1 = {"x": 123}
        message2 = {"y": None, "x": "abc"}
        bytes_f = BytesIO()
        destination = FileDestination(file=bytes_f)
        destination(message1)
        destination(message2)
        self.assertEqual(
            [json.loads(line) for line in bytes_f.getvalue().splitlines()],
            [message1, message2],
        )

    def test_filedestination_custom_encoder(self):
        """
        L{FileDestionation} can use a custom encoder.
        """
        custom = object()

        class CustomEncoder(pyjson.JSONEncoder):
            def default(self, o):
                if o is custom:
                    return "CUSTOM!"
                else:
                    return pyjson.JSONEncoder.default(self, o)

        message = {"x": 123, "z": custom}
        f = BytesIO()
        destination = FileDestination(file=f, encoder=CustomEncoder)
        destination(message)
        self.assertEqual(
            json.loads(f.getvalue().splitlines()[0]), {"x": 123, "z": "CUSTOM!"}
        )

    def test_filedestination_flushes(self):
        """
        L{FileDestination} flushes after every write, to ensure logs get
        written out even if the local buffer hasn't filled up.
        """
        path = mktemp()
        # File with large buffer:
        f = open(path, "wb", 1024 * 1024 * 10)
        # and a small message that won't fill the buffer:
        message1 = {"x": 123}

        destination = FileDestination(file=f)
        destination(message1)

        # Message got written even though buffer wasn't filled:
        self.assertEqual(
            [json.loads(line) for line in open(path, "rb").read().splitlines()],
            [message1],
        )

    def test_filedestination_writes_json_unicode(self):
        """
        L{FileDestination} writes JSON-encoded messages to file that only
        accepts Unicode.
        """
        message = {"x": "\u1234"}
        unicode_f = StringIO()
        destination = FileDestination(file=unicode_f)
        destination(message)
        self.assertEqual(pyjson.loads(unicode_f.getvalue()), message)

    def test_filedestination_unwriteable_file(self):
        """
        L{FileDestination} raises a runtime error if the given file isn't writeable.
        """
        path = mktemp()
        open(path, "w").close()
        f = open(path, "r")
        with self.assertRaises(RuntimeError):
            FileDestination(f)
