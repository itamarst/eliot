"""
Tests for L{eliot._message}.
"""

from __future__ import unicode_literals

from six import text_type as unicode
from unittest import TestCase
import time

try:
    from twisted.python.failure import Failure
except ImportError:
    Failure = None

from .._message import Message, _defaultAction
from .._output import MemoryLogger
from .._action import Action, startAction


class MessageTests(TestCase):
    """
    Test for L{Message}.
    """
    def test_new(self):
        """
        L{Message.new} returns a new L{Message} that is initialized with the
        given keyword arguments as its contents.
        """
        msg = Message.new(key="value", another=2)
        self.assertEqual(msg.contents(), {"key": "value", "another": 2})


    def test_contentsCopies(self):
        """
        L{Message.contents} returns a copy of the L{Message} contents.
        """
        msg = Message.new(key="value")
        del msg.contents()["key"]
        self.assertEqual(msg.contents(), {"key": "value"})


    def test_bindOverwrites(self):
        """
        L{Message.bind} returns a new L{Message} whose contents include the
        additional given fields.
        """
        msg = Message.new(key="value", another=2)
        another = msg.bind(another=3, more=4)
        self.assertIsInstance(another, Message)
        self.assertEqual(another.contents(), {"key": "value", "another": 3,
                                              "more": 4})


    def test_bindPreservesOriginal(self):
        """
        L{Message.bind} does not mutate the instance it is called on.
        """
        msg = Message.new(key=4)
        msg.bind(key=6)
        self.assertEqual(msg.contents(), {"key": 4})


    def test_writeCallsLoggerWrite(self):
        """
        L{Message.write} calls the given logger's C{write} method with a
        dictionary that is superset of the L{Message} contents.
        """
        logger = MemoryLogger()
        msg = Message.new(key=4)
        msg.write(logger)
        self.assertEqual(len(logger.messages), 1)
        self.assertEqual(logger.messages[0]["key"], 4)


    def test_writeCreatesNewDictionary(self):
        """
        L{Message.write} creates a new dictionary on each call.

        This is important because we mutate the dictionary in
        ``Logger.write``, so we want to make sure the ``Message`` is unchanged
        in that case. In general we want ``Message`` objects to be effectively
        immutable.
        """
        class Logger(list):
            def write(self, d, serializer):
                self.append(d)
        logger = Logger()
        msg = Message.new(key=4)
        msg.write(logger)
        logger[0]["key"] = 5
        msg.write(logger)
        self.assertEqual(logger[1]["key"], 4)


    def test_defaultTime(self):
        """
        L{Message._time} returns L{time.time} by default.
        """
        msg = Message({})
        self.assertIs(msg._time, time.time)


    def test_writeAddsTimestamp(self):
        """
        L{Message.write} adds a C{"timestamp"} field to the dictionary written
        to the logger, with the current time in seconds since the epoch.
        """
        logger = MemoryLogger()
        msg = Message.new(key=4)
        timestamp = 1387299889.153187625
        msg._time = lambda: timestamp
        msg.write(logger)
        self.assertEqual(logger.messages[0]["timestamp"], timestamp)


    def test_explicitAction(self):
        """
        L{Message.write} adds the identification fields from the given
        L{Action} to the dictionary written to the logger.
        """
        logger = MemoryLogger()
        action = Action(logger, "unique", "/", "sys:thename")
        msg = Message.new(key=2)
        msg.write(logger, action)
        written = logger.messages[0]
        del written["timestamp"]
        self.assertEqual(written,
                         {"task_uuid": "unique",
                          "task_level": "/1",
                          "key": 2})


    def test_implicitAction(self):
        """
        If no L{Action} is specified, L{Message.write} adds the identification
        fields from the current execution context's L{Action} to the
        dictionary written to the logger.
        """
        action = Action(MemoryLogger(), "unique", "/", "sys:thename")
        logger = MemoryLogger()
        msg = Message.new(key=2)
        with action:
            msg.write(logger)
        written = logger.messages[0]
        del written["timestamp"]
        self.assertEqual(written,
                         {"task_uuid": "unique",
                          "task_level": "/1",
                          "key": 2})


    def test_defaultAction(self):
        """
        If no L{Action} is specified, and the current execution context has no
        L{Action}, the process-specific global L{Action} is used.

        This ensures all messages have a unique identity, as specified by
        task_uuid/task_level.
        """
        logger = MemoryLogger()
        msg = Message.new(key=2)
        msg.write(logger)
        written = logger.messages[0]
        del written["timestamp"]
        next_task_level = _defaultAction._nextTaskLevel()
        prefix, suffix = next_task_level.split("/", 1)
        expected_task_level = "%s/%s" % (prefix, unicode(int(suffix) - 1))
        self.assertEqual(written,
                         {"task_uuid":
                              _defaultAction._identification["task_uuid"],
                          "task_level": expected_task_level,
                          "key": 2})


    def test_actionCounter(self):
        """
        Each message written within the context of an L{Action} gets its
        C{task_level} field incremented.
        """
        logger = MemoryLogger()
        msg = Message.new(key=2)
        with startAction(logger, "sys:thename"):
            for i in range(4):
                msg.write(logger)
        # We expect 6 messages: start action, 4 standalone messages, finish
        # action:
        self.assertEqual([m["task_level"] for m in logger.messages],
                         ["/1", "/2", "/3", "/4", "/5", "/6"])


    def test_writePassesSerializer(self):
        """
        If a L{Message} is created with a serializer, it is passed as a second
        argument to the logger when C{write} is called.
        """
        class ListLogger(list):
            def write(self, dictionary, serializer):
                self.append(serializer)
        logger = ListLogger()
        serializer = object()
        msg = Message({}, serializer)
        msg.write(logger)
        self.assertIs(logger[0], serializer)


    def test_serializerPassedInBind(self):
        """
        The L{Message} returned by L{Message.bind} includes the serializer
        passed to the parent.
        """
        serializer = object()
        msg = Message({}, serializer)
        msg2 = msg.bind(x=1)
        self.assertIs(msg2._serializer, serializer)


    def test_newWithSerializer(self):
        """
        L{Message.new} can accept a serializer.
        """
        serializer = object()
        msg = Message.new(serializer, x=1)
        self.assertIs(msg._serializer, serializer)
