"""
Utilities to aid unit testing L{eliot} and code that uses it.
"""

from __future__ import unicode_literals

from unittest import SkipTest
from functools import wraps

from pyrsistent import PClass, field
from six import text_type

from ._action import (
    ACTION_STATUS_FIELD,
    ACTION_TYPE_FIELD,
    STARTED_STATUS,
    FAILED_STATUS,
    SUCCEEDED_STATUS, )
from ._message import MESSAGE_TYPE_FIELD, TASK_LEVEL_FIELD, TASK_UUID_FIELD
from ._output import MemoryLogger
from . import _output

COMPLETED_STATUSES = (FAILED_STATUS, SUCCEEDED_STATUS)


def issuperset(a, b):
    """
    Use L{assertContainsFields} instead.

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


class LoggedAction(PClass):
    """
    An action whose start and finish messages have been logged.

    @ivar startMessage: A C{dict}, the start message contents. Also
        available as C{start_message}.

    @ivar endMessage: A C{dict}, the end message contents (in both success and
        failure cases). Also available as C{end_message}.

    @ivar children: A C{list} of direct child L{LoggedMessage} and
        L{LoggedAction} instances.
    """
    startMessage = field(mandatory=True)
    endMessage = field(mandatory=True)
    children = field(mandatory=True)

    def __new__(cls, startMessage, endMessage, children):
        return PClass.__new__(
            cls,
            startMessage=startMessage,
            endMessage=endMessage,
            children=children)

    @property
    def start_message(self):
        return self.startMessage

    @property
    def end_message(self):
        return self.endMessage

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

        @param level: The C{task_level} of the action's start message,
            e.g. C{"/1/2/1"}.

        @param messages: A list of message C{dict}s.

        @return: L{LoggedAction} constructed from start and finish messages for
            this specific action.

        @raises: L{ValueError} if one or both of the action's messages cannot be
            found.
        """
        startMessage = None
        endMessage = None
        children = []
        levelPrefix = level[:-1]

        for message in messages:
            if message[TASK_UUID_FIELD] != uuid:
                # Different task altogether:
                continue

            messageLevel = message[TASK_LEVEL_FIELD]

            if messageLevel[:-1] == levelPrefix:
                status = message.get(ACTION_STATUS_FIELD)
                if status == STARTED_STATUS:
                    startMessage = message
                elif status in COMPLETED_STATUSES:
                    endMessage = message
                else:
                    # Presumably a message in this action:
                    children.append(LoggedMessage(message))
            elif (
                len(messageLevel) == len(levelPrefix) + 2
                and messageLevel[:-2] == levelPrefix
                and messageLevel[-1] == 1):
                # If start message level is [1], [1, 2, 1] implies first
                # message of a direct child.
                child = klass.fromMessages(
                    uuid, message[TASK_LEVEL_FIELD], messages)
                children.append(child)
        if startMessage is None or endMessage is None:
            raise ValueError(uuid, level)
        return klass(startMessage, endMessage, children)

    # PEP 8 variant:
    from_messages = fromMessages

    @classmethod
    def of_type(klass, messages, actionType):
        """
        Find all L{LoggedAction} of the specified type.

        @param messages: A list of message C{dict}s.

        @param actionType: A L{eliot.ActionType}, the type of the actions to
            find, or the type as a C{str}.

        @return: A C{list} of L{LoggedAction}.
        """
        if not isinstance(actionType, text_type):
            actionType = actionType.action_type
        result = []
        for message in messages:
            if (
                message.get(ACTION_TYPE_FIELD) == actionType
                and message[ACTION_STATUS_FIELD] == STARTED_STATUS):
                result.append(
                    klass.fromMessages(
                        message[TASK_UUID_FIELD], message[TASK_LEVEL_FIELD],
                        messages))
        return result

    # Backwards compat:
    ofType = of_type

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
        return self.endMessage[ACTION_STATUS_FIELD] == SUCCEEDED_STATUS

    def type_tree(self):
        """Return dictionary of all child action and message types.

        Actions become dictionaries that look like
        C{{<action_type>: [<child_message_type>, <child_action_dict>]}}

        @return: C{dict} where key is action type, and value is list of child
            types: either strings for messages, or dicts for actions.
        """
        children = []
        for child in self.children:
            if isinstance(child, LoggedAction):
                children.append(child.type_tree())
            else:
                children.append(child.message[MESSAGE_TYPE_FIELD])
        return {self.startMessage[ACTION_TYPE_FIELD]: children}


class LoggedMessage(PClass):
    """
    A message that has been logged.

    @ivar message: A C{dict}, the message contents.
    """
    message = field(mandatory=True)

    def __new__(cls, message):
        return PClass.__new__(cls, message=message)

    @classmethod
    def of_type(klass, messages, messageType):
        """
        Find all L{LoggedMessage} of the specified type.

        @param messages: A list of message C{dict}s.

        @param messageType: A L{eliot.MessageType}, the type of the messages
            to find, or the type as a L{str}.

        @return: A C{list} of L{LoggedMessage}.
        """
        result = []
        if not isinstance(messageType, text_type):
            messageType = messageType.message_type
        for message in messages:
            if message.get(MESSAGE_TYPE_FIELD) == messageType:
                result.append(klass(message))
        return result

    # Backwards compat:
    ofType = of_type


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
            skipped = False

            kwargs["logger"] = logger = MemoryLogger()
            self.addCleanup(logger.validate)

            def checkForUnflushed():
                if not skipped and logger.tracebackMessages:
                    raise UnflushedTracebacks(logger.tracebackMessages)

            self.addCleanup(checkForUnflushed)
            # TestCase runs cleanups in reverse order, and we want this to
            # run *before* tracebacks are checked:
            if assertion is not None:
                self.addCleanup(lambda: skipped or assertion(
                    self, logger, *assertionArgs, **assertionKwargs))
            try:
                return function(self, *args, **kwargs)
            except SkipTest:
                skipped = True
                raise

        return wrapper

    return decorator


# PEP 8 variant:
validate_logging = validateLogging


def capture_logging(assertion, *assertionArgs, **assertionKwargs):
    """
    Capture and validate all logging that doesn't specify a L{Logger}.

    See L{validate_logging} for details on the rest of its behavior.
    """

    def decorator(function):
        @validate_logging(assertion, *assertionArgs, **assertionKwargs)
        @wraps(function)
        def wrapper(self, *args, **kwargs):
            logger = kwargs["logger"]
            current_logger = _output._DEFAULT_LOGGER
            _output._DEFAULT_LOGGER = logger

            def cleanup():
                _output._DEFAULT_LOGGER = current_logger

            self.addCleanup(cleanup)
            return function(self, logger)

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
    testCase.assertTrue(messages, "No messages of type %s" % (messageType, ))
    loggedMessage = messages[0]
    assertContainsFields(testCase, loggedMessage.message, fields)
    return loggedMessage


def assertHasAction(
    testCase, logger, actionType, succeeded, startFields=None, endFields=None):
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

    @return: The first found L{LoggedAction} of the given type, if field
        validation succeeded.

    @raises AssertionError: No action was found, or the fields were not superset
        of given fields.
    """
    if startFields is None:
        startFields = {}
    if endFields is None:
        endFields = {}
    actions = LoggedAction.ofType(logger.messages, actionType)
    testCase.assertTrue(actions, "No actions of type %s" % (actionType, ))
    action = actions[0]
    testCase.assertEqual(action.succeeded, succeeded)
    assertContainsFields(testCase, action.startMessage, startFields)
    assertContainsFields(testCase, action.endMessage, endFields)
    return action
