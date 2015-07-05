"""
Tests for L{eliot._output}.
"""

from __future__ import unicode_literals

from sys import stdout
from unittest import TestCase, skipIf
# Make sure to use StringIO that only accepts unicode:
from io import BytesIO, StringIO
import json as pyjson

from six import PY3, PY2

from zope.interface.verify import verifyClass

from .._output import (
    MemoryLogger, ILogger, Destinations, Logger, fast_json as json, to_file,
    FileDestination, _DestinationsSendError
    )
from .._message import _defaultAction
from .._validation import ValidationError, Field, _MessageSerializer
from .._traceback import writeTraceback
from ..testing import assertContainsFields


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
        logger.write({'a': 'b'})
        logger.write({'c': 1})
        self.assertEqual(logger.messages, [{'a': 'b'}, {'c': 1}])
        logger.validate()


    def test_notStringFieldKeys(self):
        """
        Field keys must be unicode or bytes; if not L{MemoryLogger.validate}
        raises a C{TypeError}.
        """
        logger = MemoryLogger()
        logger.write({123: 'b'})
        self.assertRaises(TypeError, logger.validate)


    @skipIf(PY3, "Python 3 json module makes it impossible to use bytes as keys")
    def test_bytesFieldKeys(self):
        """
        Field keys can be bytes containing utf-8 encoded Unicode.
        """
        logger = MemoryLogger()
        logger.write({u'\u1234'.encode("utf-8"): 'b'})
        logger.validate()


    def test_bytesMustBeUTF8(self):
        """
        Field keys can be bytes, but only if they're UTF-8 encoded Unicode.
        """
        logger = MemoryLogger()
        logger.write({'\u1234'.encode("utf-16"): 'b'})
        self.assertRaises(UnicodeDecodeError, logger.validate)


    def test_serializer(self):
        """
        L{MemoryLogger.validate} calls the given serializer's C{validate()}
        method with the message.
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
        self.assertEqual(validator, [])
        logger.validate()
        self.assertEqual(validator, [message])


    def test_failedValidation(self):
        """
        L{MemoryLogger.validate} will allow exceptions raised by the serializer
        to pass through.
        """
        serializer = _MessageSerializer(
            [Field.forValue("message_type", "mymessage", u"The type")])
        logger = MemoryLogger()
        logger.write({"message_type": "wrongtype"}, serializer)
        self.assertRaises(ValidationError, logger.validate)


    def test_JSON(self):
        """
        L{MemoryLogger.validate} will encode the output of serialization to
        JSON.
        """
        serializer = _MessageSerializer(
            [Field.forValue("message_type", "type", u"The type"),
             Field("foo", lambda value: object(), u"The type")])
        logger = MemoryLogger()
        logger.write({"message_type": "type",
                      "foo": "will become object()"}, serializer)
        self.assertRaises(TypeError, logger.validate)


    def test_serialize(self):
        """
        L{MemoryLogger.serialize} returns a list of serialized versions of the
        logged messages.
        """
        serializer = _MessageSerializer(
            [Field.forValue("message_type", "mymessage", "The type"),
             Field("length", len, "The length")])
        messages = [{"message_type": "mymessage", "length": "abc"},
                    {"message_type": "mymessage", "length": "abcd"}]
        logger = MemoryLogger()
        for message in messages:
            logger.write(message, serializer)
        self.assertEqual(logger.serialize(),
                         [{"message_type": "mymessage", "length": 3},
                          {"message_type": "mymessage", "length": 4}])


    def test_serializeCopies(self):
        """
        L{MemoryLogger.serialize} does not mutate the original logged messages.
        """
        serializer = _MessageSerializer(
            [Field.forValue("message_type", "mymessage", "The type"),
             Field("length", len, "The length")])
        message = {"message_type": "mymessage", "length": "abc"}
        logger = MemoryLogger()
        logger.write(message, serializer)
        logger.serialize()
        self.assertEqual(logger.messages[0]["length"], "abc")


    def writeTraceback(self, logger, exception):
        """
        Write an exception as a traceback to the logger.
        """
        try:
            raise exception
        except:
            writeTraceback(logger)


    def test_tracebacksCauseTestFailure(self):
        """
        Logging a traceback to L{MemoryLogger} will add its exception to
        L{MemoryLogger.tracebackMessages}.
        """
        logger = MemoryLogger()
        exception = Exception()
        self.writeTraceback(logger, exception)
        self.assertEqual(logger.tracebackMessages[0]["reason"], exception)


    def test_flushTracebacksNoTestFailure(self):
        """
        Any tracebacks cleared by L{MemoryLogger.flushTracebacks} (as specified
        by exception type) are removed from
        L{MemoryLogger.tracebackMessages}.
        """
        logger = MemoryLogger()
        exception = RuntimeError()
        self.writeTraceback(logger, exception)
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
            self.writeTraceback(logger, exc)
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
        self.writeTraceback(logger, exception)
        logger.flushTracebacks(KeyError)
        self.assertEqual(logger.tracebackMessages[0]["reason"], exception)


    def test_flushTracebacksUnflushedUnreturned(self):
        """
        Any tracebacks uncleared by L{MemoryLogger.flushTracebacks} (because they
        are of a different type) are not returned.
        """
        logger = MemoryLogger()
        exception = RuntimeError()
        self.writeTraceback(logger, exception)
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
            ([], [], []))



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
        destinations.add(dest.append)
        destinations.add(dest2.append)
        destinations.send(message)
        self.assertEqual(dest, [message])
        self.assertEqual(dest2, [message])


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

        message = {u"hello": 123}
        self.assertRaises(_DestinationsSendError,
                          destinations.send, {u"hello": 123})
        self.assertEqual((dest, dest3), ([message], [message]))


    def test_destinationExceptionContinue(self):
        """
        If a destination throws an exception, future messages are still
        sent to it.
        """
        destinations = Destinations()
        dest = BadDestination()
        destinations.add(dest)

        self.assertRaises(_DestinationsSendError,
                          destinations.send, {u"hello": 123})
        destinations.send({u"hello": 200})
        self.assertEqual(dest, [{u"hello": 200}])


    def test_remove(self):
        """
        A destination removed with L{Destinations.remove} will no longer
        receive messages from L{Destionations.add} calls.
        """
        destinations = Destinations()
        message = {u"hello": 123}
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
            [Field.forValue("message_type", "mymessage", u"The type"),
             Field("length", len, "The length of a thing"),
             ])
        logger.write({"message_type": "mymessage",
                      "length": "thething"},
                     serializer)
        self.assertEqual(written,
                         [{"message_type": "mymessage",
                           "length": 8}])


    def test_passedInDictionaryUnmodified(self):
        """
        The dictionary passed in to L{Logger.write} is not modified.
        """
        logger, written = makeLogger()

        serializer = _MessageSerializer(
            [Field.forValue("message_type", "mymessage", u"The type"),
             Field("length", len, "The length of a thing"),
             ])
        d = {"message_type": "mymessage",
             "length": "thething"}
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

        dictionary = {badobject(): 123,
                      123: badobject()}
        badMessage = "eliot: unknown, unicode() raised exception"
        self.assertEqual(eval(Logger()._safeUnicodeDictionary(dictionary)),
                         {badMessage: "123",
                          "123": badMessage})


    def test_safeUnicodeDictionaryFallback(self):
        """
        If converting the dictionary failed for some reason,
        L{Logger._safeUnicodeDictionary} runs C{repr} on the object.
        """
        self.assertEqual(Logger()._safeUnicodeDictionary(None),
                         "None")


    def test_safeUnicodeDictionaryFallbackFailure(self):
        """
        If all else fails, L{Logger._safeUnicodeDictionary} just gives up.
        """
        class badobject(object):
            def __repr__(self):
                raise TypeError()

        self.assertEqual(Logger()._safeUnicodeDictionary(badobject()),
                         "eliot: unknown, unicode() raised exception")


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
            [Field.forValue("message_type", "mymessage", u"The type"),
             Field("fail", raiser, "Serialization fail"),
             ])
        message = {"message_type": "mymessage",
                   "fail": "will"}
        logger.write(message, serializer)
        self.assertEqual(len(written), 2)
        tracebackMessage = written[0]
        assertContainsFields(self, tracebackMessage,
                             {'exception':
                              '%s.RuntimeError' % (RuntimeError.__module__,),
                              'message_type': 'eliot:traceback'})
        self.assertIn("RuntimeError: oops", tracebackMessage['traceback'])
        # Calling _safeUnicodeDictionary multiple times leads to
        # inconsistent results due to hash ordering, so compare contents:
        assertContainsFields(self, written[1],
                             {"message_type": "eliot:serialization_failure",
                              })
        self.assertEqual(eval(written[1]["message"]),
                         dict((repr(key), repr(value)) for
                              (key, value) in message.items()))


    def test_destinationExceptionCaught(self):
        """
        If a destination throws an exception, an appropriate error is
        logged.
        """
        logger = Logger()
        logger._time = lambda: 1234.5
        logger._destinations = Destinations()
        dest = BadDestination()
        logger._destinations.add(dest)

        message = {"hello": 123}
        logger.write({"hello": 123})
        assertContainsFields(
            self, dest[0],
            {"message_type": "eliot:destination_failure",
             "task_uuid": _defaultAction._identification["task_uuid"],
             "message": logger._safeUnicodeDictionary(message),
             "timestamp": 1234.5,
             "reason": "ono",
             "exception": "eliot.tests.test_output.MyException"})


    def test_destinationMultipleExceptionsCaught(self):
        """
        If multiple destinations throw an exception, an appropriate error is
        logged for each.
        """
        logger = Logger()
        logger._time = lambda: 1234.5
        logger._destinations = Destinations()
        logger._destinations.add(BadDestination())
        logger._destinations.add(lambda msg: 1/0)
        messages = []
        logger._destinations.add(messages.append)

        try:
            1/0
        except ZeroDivisionError as e:
            zero_divide = str(e)
        zero_type = ZeroDivisionError.__module__ + ".ZeroDivisionError"

        # There is no way to get next level without mutating
        # some state. We create a task_level, and we know the next
        # two messages will be children of _defaultAction, so
        # their levels will be consectuive.
        task_level = _defaultAction._task_level.next_child()


        message = {"hello": 123}
        logger.write({"hello": 123})
        self.assertEqual(
            messages,
            [message,
             {"message_type": "eliot:destination_failure",
              "message": logger._safeUnicodeDictionary(message),
              "task_uuid": _defaultAction._identification["task_uuid"],
              "task_level": [task_level.level[0] + 1],
              "reason": "ono",
              "timestamp": 1234.5,
              "exception": "eliot.tests.test_output.MyException"},
             {"message_type": "eliot:destination_failure",
              "message": logger._safeUnicodeDictionary(message),
              "task_uuid": _defaultAction._identification["task_uuid"],
              "task_level": [task_level.level[0] + 2],
              "reason": zero_divide,
              "timestamp": 1234.5,
              "exception": zero_type}])


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



class JSONTests(TestCase):
    """
    Tests for the L{json} object exposed by L{eliot._output}.
    """
    @skipIf(PY3, "Python 3 json does not support bytes as keys")
    def test_bytes(self):
        """
        L{json.dumps} uses a JSON encoder that assumes any C{bytes} are
        UTF-8 encoded Unicode.
        """
        d = {"hello \u1234".encode("utf-8"): "\u5678".encode("utf-8")}
        result = json.dumps(d)
        self.assertEqual(json.loads(result), {"hello \u1234": "\u5678"})



class PEP8Tests(TestCase):
    """
    Tests for PEP 8 method compatibility.
    """
    def test_flush_tracebacks(self):
        """
        L{MemoryLogger.flush_tracebacks} is the same as
        L{MemoryLogger.flushTracebacks}
        """
        self.assertEqual(MemoryLogger.flush_tracebacks,
                         MemoryLogger.flushTracebacks)



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
            [message1, message2])


    @skipIf(PY2, "Python 2 files always accept bytes")
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
