"""
Utilities to aid unit testing L{eliot} and code that uses it.
"""

from __future__ import unicode_literals

from collections import namedtuple
from functools import wraps

from ._output import MemoryLogger


def issuperset(a, b):
    """
    Use L{assertContainsFields} instead. To be removed in
    https://www.pivotaltracker.com/s/projects/787341/stories/63615936

    @type a: C{dict}

    @type b: C{dict}

    @return: Boolean indicating whether C{a} has all key/value pairs that C{b}
        does.
    """
    aItems = a.items()
    return all(pair in aItems for pair in b.items())


def assertContainsFields(test, message, fields):
    """
    Assert that the given message contains the given fields.

    @param test: L{unittest.TestCase} being run.

    @param message: C{dict}, the message we are checking.

    @param fields: C{dict}, the fields we expect the message to have.

    @raises AssertionError: If the message doesn't contain the fields.
    """
    messageSubset = dict([(key, value) for key, value in message.items()
                          if key in fields])
    test.assertEqual(messageSubset, fields)



class LoggedAction(namedtuple(
        "LoggedAction", "startMessage endMessage children")):
    """
    An action whose start and finish messages have been logged.

    @ivar startMessage: A C{dict}, the start message contents.

    @ivar endMessage: A C{dict}, the end message contents (in both success and
        failure cases).

    @ivar children: A C{list} of direct child L{LoggedMessage} and
        L{LoggedAction} instances.
    """
    @classmethod
    def fromMessages(klass, uuid, level, messages):
        """
        Given a task uuid and level (identifying an action) and a list of
        dictionaries, create a L{LoggedAction}.

        All child messages and actions will be added as L{LoggedAction} or
        L{LoggedMessage} children. Note that some descendant messages may be
        missing if you end up logging to two or more different ILogger
        providers.

        @param uuid: The uuid of the task (C{unicode}).

        @param level: The action level, e.g. C{"/1/2/"}.

        @param messages: A list of message C{dict}s.

        @return: L{LoggedAction} constructed from start and finish messages for
            this specific action.

        @raises: L{ValueError} if one or both of the action's messages cannot be
            found.
        """
        startMessage = None
        endMessage = None
        children = []
        for message in messages:
            if message["task_uuid"] != uuid:
                # Different task altogether:
                continue

            if message["task_level"] == level:
                status = message.get("action_status")
                if status == "started":
                    startMessage = message
                elif status in ("succeeded", "failed"):
                    endMessage = message
                else:
                    # Presumably a message in this action:
                    children.append(LoggedMessage(message))
            elif "action_type" in message:
                messageLevel = message["task_level"]
                # If parent level is /1/, /2/ is a sibling, /1/2/ is a direct
                # child and /1/2/1/ is a grandchild. We only want direct
                # children.
                if (messageLevel.startswith(level) and
                    messageLevel[len(level):].count("/") == 1 and
                    message["action_status"] == "started"):
                    # Passing in all messages is inefficient, but probably fine
                    # given we'll only testing with small numbers of messages.
                    child = klass.fromMessages(uuid, messageLevel, messages)
                    children.append(child)
        if startMessage is None or endMessage is None:
            raise ValueError(uuid, level)
        return klass(startMessage, endMessage, children)


    @classmethod
    def ofType(klass, messages, actionType):
        """
        Find all L{LoggedAction} of the specified type.

        @param messages: A list of message C{dict}s.

        @param actionType: A L{eliot.ActionType}, the type of the actions to
            find.

        @return: A C{list} of L{LoggedAction}.
        """
        result = []
        for message in messages:
            if (message.get("action_type") == actionType.action_type and
                message["action_status"] == "started"):
                result.append(klass.fromMessages(message["task_uuid"],
                                                 message["task_level"],
                                                 messages))
        return result


    def descendants(self):
        """
        Find all descendant L{LoggedAction} or L{LoggedMessage} of this
        instance.

        @return: An iterable of L{LoggedAction} and L{LoggedMessage} instances.
        """
        for child in self.children:
            yield child
            if isinstance(child, LoggedAction):
                for descendant in child.descendants():
                    yield descendant


    @property
    def succeeded(self):
        """
        Indicate whether this action succeeded.

        @return: C{bool} indicating whether the action succeeded.
        """
        return self.endMessage["action_status"] == "succeeded"



class LoggedMessage(namedtuple("LoggedMessage", "message")):
    """
    A message that has been logged.

    @ivar message: A C{dict}, the message contents.
    """
    @classmethod
    def ofType(klass, messages, messageType):
        """
        Find all L{LoggedMessage} of the specified type.

        @param messages: A list of message C{dict}s.

        @param messageType: A L{eliot.MessageType}, the type of the messages
            to find.

        @return: A C{list} of L{LoggedMessage}.
        """
        result = []
        for message in messages:
            if message.get("message_type") == messageType.message_type:
                result.append(klass(message))
        return result



class UnflushedTracebacks(Exception):
    """
    The L{MemoryLogger} had some tracebacks logged which were not flushed.

    This means either your code has a bug and logged an unexpected
    traceback. If you expected the traceback then you will need to flush it
    using L{MemoryLogger.flushTracebacks}.
    """



def validateLogging(assertion, *assertionArgs, **assertionKwargs):
    """
    Decorator factory for L{unittest.TestCase} methods to add logging
    validation.

    1. The decorated test method gets a C{logger} keyword argument, a
       L{MemoryLogger}.
    2. All messages logged to this logger will be validated at the end of
       the test.
    3. Any unflushed logged tracebacks will cause the test to fail.

    For example:

        from unittest import TestCase
        from eliot.testing import assertContainsFields, validateLogging

        class MyTests(TestCase):
            def assertFooLogging(self, logger):
                assertContainsFields(self, logger.messages[0], {"key": 123})


    @param assertion: A callable that will be called with the
       L{unittest.TestCase} instance, the logger and C{assertionArgs} and
       C{assertionKwargs} once the actual test has run, allowing for extra
       logging-related assertions on the effects of the test. Use L{None} if you
       want the cleanup assertions registered but no custom assertions.

    @param assertionArgs: Additional positional arguments to pass to
        C{assertion}.

    @param assertionKwargs: Additional keyword arguments to pass to
        C{assertion}.
    """
    def decorator(function):
        @wraps(function)
        def wrapper(self, *args, **kwargs):
            kwargs["logger"] = logger = MemoryLogger()
            self.addCleanup(logger.validate)
            def checkForUnflushed():
                if logger.tracebackMessages:
                    raise UnflushedTracebacks(logger.tracebackMessages)
            self.addCleanup(checkForUnflushed)
            # TestCase runs cleanups in reverse order, and we want this to
            # run *before* tracebacks are checked:
            if assertion is not None:
                self.addCleanup(lambda: assertion(
                    self, logger, *assertionArgs, **assertionKwargs))
            return function(self, *args, **kwargs)
        return wrapper
    return decorator



def assertHasMessage(testCase, logger, messageType, fields=None):
    """
    Assert that the given logger has a message of the given type, and the first
    message found of this type has the given fields.

    This can be used as the assertion function passed to L{validateLogging} or
    as part of a unit test.

    @param testCase: L{unittest.TestCase} instance.

    @param logger: L{eliot.MemoryLogger} whose messages will be checked.

    @param messageType: L{eliot.MessageType} indicating which message we're
        looking for.

    @param fields: The first message of the given type found must have a
        superset of the given C{dict} as its fields. If C{None} then fields are
        not checked.

    @return: The first found L{LoggedMessage} of the given type, if field
        validation succeeded.

    @raises AssertionError: No message was found, or the fields were not
        superset of given fields.
    """
    if fields is None:
        fields = {}
    messages = LoggedMessage.ofType(logger.messages, messageType)
    testCase.assertTrue(messages, "No messages of type %s" % (messageType,))
    loggedMessage = messages[0]
    assertContainsFields(testCase, loggedMessage.message, fields)
    return loggedMessage



def assertHasAction(testCase, logger, actionType, succeeded, startFields=None,
                    endFields=None):
    """
    Assert that the given logger has an action of the given type, and the first
    action found of this type has the given fields and success status.

    This can be used as the assertion function passed to L{validateLogging} or
    as part of a unit test.

    @param testCase: L{unittest.TestCase} instance.

    @param logger: L{eliot.MemoryLogger} whose messages will be checked.

    @param actionType: L{eliot.ActionType} indicating which message we're
        looking for.

    @param succeeded: Expected success status of the action, a C{bool}.

    @param startFields: The first action of the given type found must have a
        superset of the given C{dict} as its start fields. If C{None} then
        fields are not checked.

    @param endFields: The first action of the given type found must have a
        superset of the given C{dict} as its end fields. If C{None} then
        fields are not checked.

    @return: The first found L{LoggedAction} of the given type, if field validation
        succeeded.

    @raises AssertionError: No action was found, or the fields were not superset
        of given fields.
    """
    if startFields is None:
        startFields = {}
    if endFields is None:
        endFields = {}
    actions = LoggedAction.ofType(logger.messages, actionType)
    testCase.assertTrue(actions, "No actions of type %s" % (actionType,))
    action = actions[0]
    testCase.assertEqual(action.succeeded, succeeded)
    assertContainsFields(testCase, action.startMessage, startFields)
    assertContainsFields(testCase, action.endMessage, endFields)
    return action
