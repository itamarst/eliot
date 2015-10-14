"""
Parse a stream of serialized messages into a forest of
``WrittenAction`` and ``WrittenMessage`` objects.

# XXX maybe move Written* here.
"""

from pyrsistent import PClass, field, pmap_field, optional

from ._message import WrittenMessage
from ._action import TaskLevel, WrittenAction


#@implementer(IWrittenAction)
class MissingAction(PClass):
    end_message = field(type=optional(WrittenMessage), mandatory=True)
    _children = pmap_field(TaskLevel, object)


class Task(PClass):
    """
    A tree of actions with the same task UUID.
    """
    _root = field(type=(MissingAction, WrittenAction, WrittenMessage),
                  mandatory=True)

    @classmethod
    def from_messages(cls, messages):
        task = cls.create(messages[0])
        for message in messages[1:]:
            task = task.add(message)
        return task

    @classmethod
    def create(cls, first_message):
        pass

    def add(self, message):
        pass
