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
        Freeze this message for logging, registering it with C{action}.

        @return: A L{PMap} with added C{timestamp}, C{task_uuid}, and
            C{task_level} entries.
        """
        if action is None:
            action = currentAction()
        if action is None:
            action = _defaultAction
        return self._contents.update({
            'timestamp': self._timestamp(),
            'task_uuid': action._identification['task_uuid'],
            'task_level': action._nextTaskLevel().level
        })

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
        logged_dict = self._freeze(action=action)
        logger.write(dict(logged_dict), self._serializer)
        return WrittenMessage.from_dict(logged_dict)



class WrittenMessage(PClass):
    """
    A L{Message} that has been logged.

    @ivar _logged_dict: The originally logged dictionary.
    """

    _logged_dict = field()

    @property
    def timestamp(self):
        """
        The Unix timestamp of when the message was logged.
        """
        return self._logged_dict['timestamp']


    @property
    def task_uuid(self):
        """
        The UUID of the task in which the message was logged.
        """
        return self._logged_dict['task_uuid']


    @property
    def task_level(self):
        """
        The L{TaskLevel} of this message appears within the task.
        """
        return TaskLevel(level=self._logged_dict['task_level'])


    @property
    def contents(self):
        """
        A C{PMap}, the message contents without Eliot metadata.
        """
        return self._logged_dict.discard(
            'timestamp').discard('task_uuid').discard('task_level')


    @classmethod
    def from_dict(cls, logged_dictionary):
        """
        Reconstruct a L{WrittenMessage} from a logged dictionary.

        @param logged_dictionary: A C{PMap} representing a parsed log entry.
        @return: A L{WrittenMessage} for that dictionary.
        """
        return cls(_logged_dict=logged_dictionary)


    def as_dict(self):
        """
        Return the dictionary that was used to write this message.

        @return: A C{dict}, as might be logged by Eliot.
        """
        return self._logged_dict




# Import at end to deal with circular imports:
from ._action import currentAction, Action, TaskLevel
from . import _output

# The default Action to use as a context for messages, if no other Action is the
# context. This ensures all messages have a unique identity, as specified by
# task_uuid/task_level.
_defaultAction = Action(None, u"%s" % (uuid4(),), TaskLevel(level=[]),
                        "eliot:default")
