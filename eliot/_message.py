"""
Log messages and related utilities.
"""

from __future__ import unicode_literals

import time
from uuid import uuid4

from pyrsistent import PClass, field, pmap


class Message(object):
    """
    A log message.

    Messages are basically dictionaries, mapping "fields" to "values". Field
    names should not start with C{'_'}, as those are reserved for system use
    (e.g. C{"_id"} is used by Elasticsearch for unique message identifiers and
    may be auto-populated by logstash).
    """
    # Overrideable for testing purposes:
    _time = time.time


    @classmethod
    def new(_class, _serializer=None, **fields):
        """
        Create a new L{Message}.

        The keyword arguments will become the initial contents of the L{Message}.

        @param _serializer: A positional argument, either C{None} or a
            L{eliot._validation._MessageSerializer} with which a
            L{eliot.ILogger} may choose to serialize the message. If you're
            using L{eliot.MessageType} this will be populated for you.

        @return: The new L{Message}
        """
        return _class(fields, _serializer)


    @classmethod
    def log(_class, **fields):
        """
        Write a new L{Message} to the default L{Logger}.

        The keyword arguments will become contents of the L{Message}.
        """
        _class.new(**fields).write()


    def __init__(self, contents, serializer=None):
        """
        You can also use L{Message.new} to create L{Message} objects.

        @param contents: The contents of this L{Message}, a C{dict} whose keys
           must be C{unicode}, or text that has been UTF-8 encoded to
           C{bytes}.

        @param serializer: Either C{None}, or
            L{eliot._validation._MessageSerializer} with which a
            L{eliot.Logger} may choose to serialize the message. If you're
            using L{eliot.MessageType} this will be populated for you.
        """
        self._contents = pmap(contents)
        self._serializer = serializer


    def bind(self, **fields):
        """
        Return a new L{Message} with this message's contents plus the
        additional given bindings.
        """
        return Message(self._contents.update(fields), self._serializer)


    def contents(self):
        """
        Return a copy of L{Message} contents.
        """
        return dict(self._contents)


    def _timestamp(self):
        """
        Return the current time.
        """
        return self._time()


    def _freeze(self, action=None):
        """
        Freeze this message for logging, registring it with C{action}.

        @rtype: L{WrittenMessage}
        """
        if action is None:
            action = currentAction()
        if action is None:
            action = _defaultAction
        return WrittenMessage(
            timestamp=self._timestamp(),
            task_uuid=action._identification["task_uuid"],
            task_level=action._nextTaskLevel(),
            contents=self._contents,
        )


    def write(self, logger=None, action=None):
        """
        Write the message to the given logger.

        This will additionally include a timestamp, the action context if any,
        and any other fields.

        Byte field names will be converted to Unicode.

        @type logger: L{eliot.ILogger} or C{None} indicating the default one.

        @param action: The L{Action} which is the context for this message. If
            C{None}, the L{Action} will be deduced from the current call
            stack.
        """
        if logger is None:
            logger = _output._DEFAULT_LOGGER
        logged = self._freeze(action=action)
        logger.write(logged.as_dict(), self._serializer)
        return logged



class WrittenMessage(PClass):
    """
    A L{Message} that has been logged.

    @ivar timestamp: The Unix timestamp of when the message was logged.
    @ivar task_uuid: The UUID of the task in which the message was logged.
    @ivar task_level: The L{TaskLevel} of this message appears within the task.
    @ivar contents: A C{pmap}, the message contents without Eliot metadata.
    """

    timestamp = field()
    task_uuid = field()
    task_level = field()
    contents = field()

    @classmethod
    def from_dict(cls, logged_dictionary):
        """
        Reconstruct a L{WrittenMessage} from a logged dictionary.

        @param logged_dictionary: A dict representing a parsed log entry.
        @return: A L{WrittenMessage} for that dictionary.
        """
        contents = logged_dictionary.copy()
        timestamp = contents.pop('timestamp')
        task_uuid = contents.pop('task_uuid')
        task_level = TaskLevel(level=contents.pop('task_level'))
        return cls(timestamp=timestamp,
                   task_uuid=task_uuid,
                   task_level=task_level,
                   contents=pmap(contents))


    def as_dict(self):
        """
        Return the dictionary that was used to write this message.

        @return: A C{dict}, as might be logged by Eliot.
        """
        return dict(self.contents.update({
            'timestamp': self.timestamp,
            'task_uuid': self.task_uuid,
            'task_level': self.task_level.level,
        }))




# Import at end to deal with circular imports:
from ._action import currentAction, Action, TaskLevel
from . import _output

# The default Action to use as a context for messages, if no other Action is the
# context. This ensures all messages have a unique identity, as specified by
# task_uuid/task_level.
_defaultAction = Action(None, u"%s" % (uuid4(),), TaskLevel(level=[]),
                        "eliot:default")
