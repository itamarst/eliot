"""
Parse a stream of serialized messages into a forest of
``WrittenAction`` and ``WrittenMessage`` objects.
"""

from __future__ import unicode_literals

from pyrsistent import PClass, pmap_field, pset_field, discard

from ._message import WrittenMessage, TASK_UUID_FIELD
from ._action import (
    TaskLevel, WrittenAction, ACTION_STATUS_FIELD, STARTED_STATUS,
    ACTION_TYPE_FIELD,
)


class Task(PClass):
    """
    A tree of actions with the same task UUID.
    """
    _nodes = pmap_field(TaskLevel, (WrittenAction, WrittenMessage))
    _completed = pset_field(TaskLevel)
    _root_level = TaskLevel(level=[])

    def root(self):
        """
        @return: The root L{WrittenAction}.
        """
        return self._nodes[self._root_level]

    def is_complete(self):
        """
        @return bool: True only if all messages in the task tree have been
        added to it.
        """
        return self._root_level in self._completed

    def _insert_action(self, node):
        """
        Add a L{WrittenAction} to the tree.

        Parent actions will be created as necessary.

        @param child: A L{WrittenAction} to add to the tree.

        @return: Updated L{Task}.
        """
        task = self
        if (node.end_message and node.start_message
            and (len(node.children) ==
                 node.end_message.task_level.level[-1] - 2)):
            # Possibly this action is complete, make sure all sub-actions
            # are complete:
            completed = True
            for child in node.children:
                if (isinstance(child, WrittenAction) and
                        child.task_level not in self._completed):
                    completed = False
                    break
            if completed:
                task = task.transform(["_completed"],
                                      lambda s: s.add(node.task_level))
        task = task.transform(["_nodes", node.task_level], node)
        return task._ensure_node_parents(node)

    def _ensure_node_parents(self, child):
        """
        Ensure the node (WrittenAction/WrittenMessage) is referenced by parent
        nodes.

        Parent actions will be created as necessary.

        @param child: A L{WrittenMessage} or L{WrittenAction} which is
            being added to the tree.

        @return: Updated L{Task}.
        """
        task_level = child.task_level
        if task_level.parent() is None:
            return self

        parent = self._nodes.get(task_level.parent())
        if parent is None:
            parent = WrittenAction(task_level=task_level.parent(),
                                   task_uuid=child.task_uuid)
        parent = parent._add_child(child)
        return self._insert_action(parent)

    def add(self, message_dict):
        """
        Update the L{Task} with a dictionary containing a serialized Eliot
        message.

        @param message_dict: Dictionary whose task UUID matches this one.

        @return: Updated L{Task}.
        """
        is_action = message_dict.get(ACTION_TYPE_FIELD) is not None
        written_message = WrittenMessage.from_dict(message_dict)
        if is_action:
            action_level = written_message.task_level.parent()
            action = self._nodes.get(action_level)
            if action is None:
                action = WrittenAction(task_level=action_level,
                                       task_uuid=message_dict[TASK_UUID_FIELD])
            if message_dict[ACTION_STATUS_FIELD] == STARTED_STATUS:
                # Either newly created MissingAction, or one created by
                # previously added descendant of the action.
                action = action._start(written_message)
            else:
                action = action._end(written_message)
            return self._insert_action(action)
        else:
            # Special case where there is no action:
            if written_message.task_level.level == [1]:
                return self.transform(
                    ["_nodes", self._root_level], written_message,
                    ["_completed"], lambda s: s.add(self._root_level))
            else:
                return self._ensure_node_parents(written_message)


class Parser(PClass):
    """
    Parse serialized Eliot messages into L{Task} instances.

    @ivar _tasks: Map from UUID to corresponding L{Task}.
    """
    _tasks = pmap_field(unicode, Task)

    def add(self, message_dict):
        """
        Update the L{} with a dictionary containing a serialized Eliot
        message.

        @param message_dict: Dictionary of serialized Eliot message.

        @return: Tuple of (list of completed L{Task} instances, updated L{Parser}).
        """
        uuid = message_dict[TASK_UUID_FIELD]
        if uuid in self._tasks:
            task = self._tasks[uuid]
        else:
            task = Task()
        task = task.add(message_dict)
        if task.is_complete():
            parser = self.transform(["_tasks", uuid], discard)
            return [task], parser
        else:
            parser = self.transform(["_tasks", uuid], task)
            return [], parser

    def incomplete_tasks(self):
        """
        @return: List of L{Task} that are not yet complete.
        """
        return list(self._tasks.values())

    @classmethod
    def parse_stream(cls, iterable):
        return
        parser = Parser()
        for message_dict in iterable:
            completed, parser = parser.add(message_dict)
            for task in completed:
                yield task
        for task in parser.incomplete_tasks():
            yield task
