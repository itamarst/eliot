"""
Support for actions and tasks.

Actions have a beginning and an eventual end, and can be nested. Tasks are
top-level actions.
"""

from __future__ import unicode_literals, absolute_import

import threading
from uuid import uuid4
from itertools import count
from contextlib import contextmanager
from warnings import warn

from pyrsistent import (
    field, PClass, optional, pmap_field, pvector_field, pvector,
)

from six import text_type as unicode, integer_types

from ._message import (
    Message,
    WrittenMessage,
    EXCEPTION_FIELD,
    REASON_FIELD,
    TASK_UUID_FIELD,
)
from ._util import safeunicode
from ._errors import _error_extraction

ACTION_STATUS_FIELD = 'action_status'
ACTION_TYPE_FIELD = 'action_type'

STARTED_STATUS = 'started'
SUCCEEDED_STATUS = 'succeeded'
FAILED_STATUS = 'failed'

VALID_STATUSES = (STARTED_STATUS, SUCCEEDED_STATUS, FAILED_STATUS)


class _ExecutionContext(threading.local):
    """
    Call stack-based context, storing the current L{Action}.

    Bit like L{twisted.python.context}, but:

    - Single purpose.
    - Allows support for Python context managers (this could easily be added
      to Twisted, though).
    - Does not require Twisted; Eliot should not require Twisted if possible.
    """
    def __init__(self):
        self._stack = []


    def push(self, action):
        """
        Push the given L{Action} to the front of the stack.

        @param action: L{Action} that will be used for log messages and as
            parent of newly created L{Action} instances.
        """
        self._stack.append(action)


    def pop(self):
        """
        Pop the front L{Action} on the stack.
        """
        self._stack.pop(-1)


    def current(self):
        """
        @return: The current front L{Action}, or C{None} if there is no
            L{Action} set.
        """
        if not self._stack:
            return None
        return self._stack[-1]


_context = _ExecutionContext()
currentAction = _context.current



class TaskLevel(PClass):
    """
    The location of a message within the tree of actions of a task.

    @ivar level: A pvector of integers. Each item indicates a child
        relationship, and the value indicates message count. E.g. C{[2,
        3]} indicates this is the third message within an action which is
        the second item in the task.
    """

    level = pvector_field(integer_types)

    # PClass really ought to provide this ordering facility for us:
    # tobgu/pyrsistent#45.

    def __lt__(self, other):
        return self.level < other.level

    def __le__(self, other):
        return self.level <= other.level

    def __gt__(self, other):
        return self.level > other.level

    def __ge__(self, other):
        return self.level >= other.level

    @classmethod
    def fromString(cls, string):
        """
        Convert a serialized Unicode string to a L{TaskLevel}.

        @param string: Output of L{TaskLevel.toString}.

        @return: L{TaskLevel} parsed from the string.
        """
        return cls(level=[int(i) for i in string.split("/") if i])


    def toString(self):
        """
        Convert to a Unicode string, for serialization purposes.

        @return: L{unicode} representation of the L{TaskLevel}.
        """
        return "/" + "/".join(map(unicode, self.level))


    def next_sibling(self):
        """
        Return the next L{TaskLevel}, that is a task at the same level as this
        one, but one after.

        @return: L{TaskLevel} which follows this one.
        """
        return TaskLevel(level=self.level.set(-1, self.level[-1] + 1))


    def child(self):
        """
        Return a child of this L{TaskLevel}.

        @return: L{TaskLevel} which is the first child of this one.
        """
        return TaskLevel(level=self.level.append(1))


    def parent(self):
        """
        Return the parent of this L{TaskLevel}, or C{None} if it doesn't have
        one.

        @return: L{TaskLevel} which is the parent of this one.
        """
        if not self.level:
            return None
        return TaskLevel(level=self.level[:-1])


    def is_sibling_of(self, task_level):
        """
        Is this task a sibling of C{task_level}?
        """
        return self.parent() == task_level.parent()


    # PEP 8 compatibility:
    from_string = fromString
    to_string = toString


_TASK_ID_NOT_SUPPLIED = object()


class Action(object):
    """
    Part of a nested heirarchy of ongoing actions.

    An action has a start and an end; a message is logged for each.

    Actions should only be used from a single thread, by implication the
    thread where they were created.

    @ivar _identification: Fields identifying this action.

    @ivar _successFields: Fields to be included in successful finish message.

    @ivar _finished: L{True} if the L{Action} has finished, otherwise L{False}.
    """
    def __init__(self, logger, task_uuid, task_level, action_type,
                 serializers=None):
        """
        Initialize the L{Action} and log the start message.

        You probably do not want to use this API directly: use L{startAction}
        or L{startTask} instead.

        @param logger: The L{eliot.ILogger} to which to write
            messages.

        @param task_uuid: The uuid of the top-level task, e.g. C{"123525"}.

        @param task_level: The action's level in the task.
        @type task_level: L{TaskLevel}

        @param action_type: The type of the action,
            e.g. C{"yourapp:subsystem:dosomething"}.

        @param serializers: Either a L{eliot._validation._ActionSerializers}
            instance or C{None}. In the latter case no validation or
            serialization will be done for messages generated by the
            L{Action}.
        """
        self._numberOfMessages = iter(count())
        self._successFields = {}
        self._logger = logger
        if isinstance(task_level, unicode):
            warn("Action should be initialized with a TaskLevel",
                 DeprecationWarning, stacklevel=2)
            task_level = TaskLevel.fromString(task_level)
        self._task_level = task_level
        self._last_child = None
        self._identification = {TASK_UUID_FIELD: task_uuid,
                                ACTION_TYPE_FIELD: action_type,
                                }
        self._serializers = serializers
        self._finished = False


    @property
    def task_uuid(self):
        """
        @return str: the current action's task UUID.
        """
        return self._identification[TASK_UUID_FIELD]


    def serializeTaskId(self):
        """
        Create a unique identifier for the current location within the task.

        The format is C{b"<task_uuid>@<task_level>"}.

        @return: L{bytes} encoding the current location within the task.
        """
        return "{}@{}".format(self._identification[TASK_UUID_FIELD],
                              self._nextTaskLevel().toString()).encode("ascii")


    @classmethod
    def continueTask(cls, logger=None, task_id=_TASK_ID_NOT_SUPPLIED):
        """
        Start a new action which is part of a serialized task.

        @param logger: The L{eliot.ILogger} to which to write
            messages, or C{None} if the default one should be used.

        @param task_id: A serialized task identifier, the output of
            L{Action.serialize_task_id}. Required.

        @return: The new L{Action} instance.
        """
        if task_id is _TASK_ID_NOT_SUPPLIED:
            raise RuntimeError("You must supply a task_id keyword argument.")
        uuid, task_level = task_id.decode("ascii").split("@")
        action = cls(logger, uuid, TaskLevel.fromString(task_level),
                     "eliot:remote_task")
        action._start({})
        return action


    # PEP 8 variants:
    serialize_task_id = serializeTaskId
    continue_task = continueTask


    def _nextTaskLevel(self):
        """
        Return the next C{task_level} for messages within this action.

        Called whenever a message is logged within the context of an action.

        @return: The message's C{task_level}.
        """
        if not self._last_child:
            self._last_child = self._task_level.child()
        else:
            self._last_child = self._last_child.next_sibling()
        return self._last_child


    def _start(self, fields):
        """
        Log the start message.

        The action identification fields, and any additional given fields,
        will be logged.

        In general you shouldn't call this yourself, instead using a C{with}
        block or L{Action.finish}.
        """
        fields[ACTION_STATUS_FIELD] = STARTED_STATUS
        fields.update(self._identification)
        if self._serializers is None:
            serializer = None
        else:
            serializer = self._serializers.start
        Message(fields, serializer).write(self._logger, self)


    def finish(self, exception=None):
        """
        Log the finish message.

        The action identification fields, and any additional given fields,
        will be logged.

        In general you shouldn't call this yourself, instead using a C{with}
        block or L{Action.finish}.

        @param exception: C{None}, in which case the fields added with
            L{Action.addSuccessFields} are used. Or an L{Exception}, in
            which case an C{"exception"} field is added with the given
            L{Exception} type and C{"reason"} with its contents.
        """
        if self._finished:
            return
        self._finished = True
        serializer = None
        if exception is None:
            fields = self._successFields
            fields[ACTION_STATUS_FIELD] = SUCCEEDED_STATUS
            if self._serializers is not None:
                serializer = self._serializers.success
        else:
            fields = _error_extraction.get_fields_for_exception(
                self._logger, exception)
            fields[EXCEPTION_FIELD] = "%s.%s" % (exception.__class__.__module__,
                                             exception.__class__.__name__)
            fields[REASON_FIELD] = safeunicode(exception)
            fields[ACTION_STATUS_FIELD] = FAILED_STATUS
            if self._serializers is not None:
                serializer = self._serializers.failure

        fields.update(self._identification)
        Message(fields, serializer).write(self._logger, self)


    def child(self, logger, action_type, serializers=None):
        """
        Create a child L{Action}.

        Rather than calling this directly, you can use L{startAction} to
        create child L{Action} using the execution context.

        @param logger: The L{eliot.ILogger} to which to write
            messages.

        @param action_type: The type of this action,
            e.g. C{"yourapp:subsystem:dosomething"}.

        @param serializers: Either a L{eliot._validation._ActionSerializers}
            instance or C{None}. In the latter case no validation or
            serialization will be done for messages generated by the
            L{Action}.
        """
        newLevel = self._nextTaskLevel()
        return self.__class__(logger,
                              self._identification[TASK_UUID_FIELD],
                              newLevel,
                              action_type,
                              serializers)


    def run(self, f, *args, **kwargs):
        """
        Run the given function with this L{Action} as its execution context.
        """
        _context.push(self)
        try:
            return f(*args, **kwargs)
        finally:
            _context.pop()


    def addSuccessFields(self, **fields):
        """
        Add fields to be included in the result message when the action
        finishes successfully.

        @param fields: Additional fields to add to the result message.
        """
        self._successFields.update(fields)


    # PEP 8 variant:
    add_success_fields = addSuccessFields


    @contextmanager
    def context(self):
        """
        Create a context manager that ensures code runs within action's context.

        The action does NOT finish when the context is exited.
        """
        _context.push(self)
        try:
            yield self
        finally:
            _context.pop()


    # Python context manager implementation:
    def __enter__(self):
        """
        Push this action onto the execution context.
        """
        _context.push(self)
        return self


    def __exit__(self, type, exception, traceback):
        """
        Pop this action off the execution context, log finish message.
        """
        _context.pop()
        self.finish(exception)


class WrongTask(Exception):
    """
    Tried to add a message to an action, but the message was from another
    task.
    """

    def __init__(self, action, message):
        Exception.__init__(
            self, 'Tried to add {} to {}. Expected task_uuid = {}, got {}'.format(
                message, action, action.task_uuid, message.task_uuid))


class WrongTaskLevel(Exception):
    """
    Tried to add a message to an action, but the task level of the message
    indicated that it was not a direct child.
    """

    def __init__(self, action, message):
        Exception.__init__(
            self, 'Tried to add {} to {}, but {} is not a sibling of {}'.format(
                message, action, message.task_level, action.task_level))


class WrongActionType(Exception):
    """
    Tried to end a message with a different action_type than the beginning.
    """

    def __init__(self, action, message):
        error_msg = 'Tried to end {} with {}. Expected action_type = {}, got {}'
        Exception.__init__(
            self, error_msg.format(
                action, message, action.action_type,
                message.contents.get(ACTION_TYPE_FIELD, '<undefined>')))


class InvalidStatus(Exception):
    """
    Tried to end a message with an invalid status.
    """

    def __init__(self, action, message):
        error_msg = 'Tried to end {} with {}. Expected status {} or {}, got {}'
        Exception.__init__(
            self, error_msg.format(
                action, message, SUCCEEDED_STATUS, FAILED_STATUS,
                message.contents.get(ACTION_STATUS_FIELD, '<undefined>')))


class DuplicateChild(Exception):
    """
    Tried to add a child to an action that already had a child at that task
    level.
    """

    def __init__(self, action, message):
        Exception.__init__(
            self, 'Tried to add {} to {}, but already had child at {}'.format(
                message, action, message.task_level))


class InvalidStartMessage(Exception):
    """
    Tried to start an action with an invalid message.
    """

    def __init__(self, message, reason):
        Exception.__init__(
            self, 'Invalid start message {}: {}'.format(message, reason))

    @classmethod
    def wrong_status(cls, message):
        return cls(message, 'must have status "STARTED"')

    @classmethod
    def wrong_task_level(cls, message):
        return cls(message, 'first message must have task level ending in 1')


class WrittenAction(PClass):
    """
    An Action that has been logged.

    This class is intended to provide a definition within Eliot of what an
    action actually is, and a means of constructing actions that are known to
    be valid.

    @ivar WrittenMessage start_message: A start message whose task UUID and
        level match this action, or C{None} if it is not yet set on the
        action.
    @ivar WrittenMessage end_message: An end message hose task UUID and
        level match this action. Can be C{None} if the action is
        unfinished.
    @ivar TaskLevel task_level: The action's task level, e.g. if start
        message has level C{[2, 3, 1]} it will be
        C{TaskLevel(level=[2, 3])}.
    @ivar UUID task_uuid: The UUID of the task to which this action belongs.
    @ivar _children: A L{pmap} from L{TaskLevel} to the L{WrittenAction} and
        L{WrittenMessage} objects that make up this action.
    """

    start_message = field(type=optional(WrittenMessage), mandatory=True,
                          initial=None)
    end_message = field(type=optional(WrittenMessage), mandatory=True,
                        initial=None)
    task_level = field(type=TaskLevel, mandatory=True)
    task_uuid = field(type=unicode, mandatory=True, factory=unicode)
    # Pyrsistent doesn't support pmap_field with recursive types.
    _children = pmap_field(TaskLevel, object)

    @classmethod
    def from_messages(cls, start_message=None, children=pvector(),
                      end_message=None):
        """
        Create a C{WrittenAction} from C{WrittenMessage}s and other
        C{WrittenAction}s.

        @param WrittenMessage start_message: A message that has
            C{ACTION_STATUS_FIELD}, C{ACTION_TYPE_FIELD}, and a C{task_level}
            that ends in C{1}, or C{None} if unavailable.
        @param children: An iterable of C{WrittenMessage} and C{WrittenAction}
        @param WrittenMessage end_message: A message that has the same
            C{action_type} as this action.

        @raise WrongTask: If C{end_message} has a C{task_uuid} that differs
            from C{start_message.task_uuid}.
        @raise WrongTaskLevel: If any child message or C{end_message} has a
            C{task_level} that means it is not a direct child.
        @raise WrongActionType: If C{end_message} has an C{ACTION_TYPE_FIELD}
            that differs from the C{ACTION_TYPE_FIELD} of C{start_message}.
        @raise InvalidStatus: If C{end_message} doesn't have an
            C{action_status}, or has one that is not C{SUCCEEDED_STATUS} or
            C{FAILED_STATUS}.
        @raise InvalidStartMessage: If C{start_message} does not have a
            C{ACTION_STATUS_FIELD} of C{STARTED_STATUS}, or if it has a
            C{task_level} indicating that it is not the first message of an
            action.

        @return: A new C{WrittenAction}.
        """
        actual_message = [message for message in
                          [start_message, end_message] + list(children)
                          if message][0]
        action = cls(
            task_level=actual_message.task_level.parent(),
            task_uuid=actual_message.task_uuid,
        )
        if start_message:
            action = action._start(start_message)
        for child in children:
            if action._children.get(child.task_level, child) != child:
                raise DuplicateChild(action, child)
            action = action._add_child(child)
        if end_message:
            action = action._end(end_message)
        return action

    @property
    def action_type(self):
        """
        The type of this action, e.g. C{"yourapp:subsystem:dosomething"}.
        """
        if self.start_message:
            return self.start_message.contents[ACTION_TYPE_FIELD]
        elif self.end_message:
            return self.end_message.contents[ACTION_TYPE_FIELD]
        else:
            return None

    @property
    def status(self):
        """
        One of C{STARTED_STATUS}, C{SUCCEEDED_STATUS}, C{FAILED_STATUS} or
        C{None}.
        """
        message = self.end_message if self.end_message else self.start_message
        if message:
            return message.contents[ACTION_STATUS_FIELD]
        else:
            return None

    @property
    def start_time(self):
        """
        The Unix timestamp of when the action started, or C{None} if there has
        been no start message added so far.
        """
        if self.start_message:
            return self.start_message.timestamp

    @property
    def end_time(self):
        """
        The Unix timestamp of when the action ended, or C{None} if there has been
        no end message.
        """
        if self.end_message:
            return self.end_message.timestamp

    @property
    def exception(self):
        """
        If the action failed, the name of the exception that was raised to cause
        it to fail. If the action succeeded, or hasn't finished yet, then
        C{None}.
        """
        if self.end_message:
            return self.end_message.contents.get(EXCEPTION_FIELD, None)

    @property
    def reason(self):
        """
        The reason the action failed. If the action succeeded, or hasn't finished
        yet, then C{None}.
        """
        if self.end_message:
            return self.end_message.contents.get(REASON_FIELD, None)

    @property
    def children(self):
        """
        The list of child messages and actions sorted by task level, excluding the
        start and end messages.
        """
        return pvector(sorted(self._children.values(), key=lambda m: m.task_level))

    def _validate_message(self, message):
        """
        Is C{message} a valid direct child of this action?

        @param message: Either a C{WrittenAction} or a C{WrittenMessage}.

        @raise WrongTask: If C{message} has a C{task_uuid} that differs from the
            action's C{task_uuid}.
        @raise WrongTaskLevel: If C{message} has a C{task_level} that means
            it's not a direct child.
        """
        if message.task_uuid != self.task_uuid:
            raise WrongTask(self, message)
        if not message.task_level.parent() == self.task_level:
            raise WrongTaskLevel(self, message)

    def _add_child(self, message):
        """
        Return a new action with C{message} added as a child.

        Assumes C{message} is not an end message.

        @param message: Either a C{WrittenAction} or a C{WrittenMessage}.

        @raise WrongTask: If C{message} has a C{task_uuid} that differs from the
            action's C{task_uuid}.
        @raise WrongTaskLevel: If C{message} has a C{task_level} that means
            it's not a direct child.

        @return: A new C{WrittenAction}.
        """
        self._validate_message(message)
        level = message.task_level
        return self.transform(('_children', level), message)

    def _start(self, start_message):
        """
        Start this action given its start message.

        @param WrittenMessage start_message: A start message that has the
            same level as this action.

        @raise InvalidStartMessage: If C{start_message} does not have a
            C{ACTION_STATUS_FIELD} of C{STARTED_STATUS}, or if it has a
            C{task_level} indicating that it is not the first message of an
            action.
        """
        if start_message.contents.get(
                ACTION_STATUS_FIELD, None) != STARTED_STATUS:
            raise InvalidStartMessage.wrong_status(start_message)
        if start_message.task_level.level[-1] != 1:
            raise InvalidStartMessage.wrong_task_level(start_message)
        return self.set(start_message=start_message)

    def _end(self, end_message):
        """
        End this action with C{end_message}.

        Assumes that the action has not already been ended.

        @param WrittenMessage end_message: An end message that has the
            same level as this action.

        @raise WrongTask: If C{end_message} has a C{task_uuid} that differs
            from the action's C{task_uuid}.
        @raise WrongTaskLevel: If C{end_message} has a C{task_level} that means
            it's not a direct child.
        @raise InvalidStatus: If C{end_message} doesn't have an
            C{action_status}, or has one that is not C{SUCCEEDED_STATUS} or
            C{FAILED_STATUS}.

        @return: A new, completed C{WrittenAction}.
        """
        action_type = end_message.contents.get(ACTION_TYPE_FIELD, None)
        if self.action_type not in (None, action_type):
            raise WrongActionType(self, end_message)
        self._validate_message(end_message)
        status = end_message.contents.get(ACTION_STATUS_FIELD, None)
        if status not in (FAILED_STATUS, SUCCEEDED_STATUS):
            raise InvalidStatus(self, end_message)
        return self.set(end_message=end_message)


def startAction(logger=None, action_type="", _serializers=None, **fields):
    """
    Create a child L{Action}, figuring out the parent L{Action} from execution
    context, and log the start message.

    You can use the result as a Python context manager, or use the
    L{Action.finish} API to explicitly finish it.

         with startAction(logger, "yourapp:subsystem:dosomething",
                          entry=x) as action:
              do(x)
              result = something(x * 2)
              action.addSuccessFields(result=result)

    Or alternatively:

         action = startAction(logger, "yourapp:subsystem:dosomething",
                              entry=x)
         with action.context():
              do(x)
              result = something(x * 2)
              action.addSuccessFields(result=result)
         action.finish()

    @param logger: The L{eliot.ILogger} to which to write messages, or
        C{None} to use the default one.

    @param action_type: The type of this action,
        e.g. C{"yourapp:subsystem:dosomething"}.

    @param _serializers: Either a L{eliot._validation._ActionSerializers}
        instance or C{None}. In the latter case no validation or serialization
        will be done for messages generated by the L{Action}.

    @param fields: Additional fields to add to the start message.

    @return: A new L{Action}.
    """
    parent = currentAction()
    if parent is None:
        return startTask(logger, action_type, _serializers, **fields)
    else:
        action = parent.child(logger, action_type, _serializers)
        action._start(fields)
        return action



def startTask(logger=None, action_type=u"", _serializers=None, **fields):
    """
    Like L{action}, but creates a new top-level L{Action} with no parent.

    @param logger: The L{eliot.ILogger} to which to write messages, or
        C{None} to use the default one.

    @param action_type: The type of this action,
        e.g. C{"yourapp:subsystem:dosomething"}.

    @param _serializers: Either a L{eliot._validation._ActionSerializers}
        instance or C{None}. In the latter case no validation or serialization
        will be done for messages generated by the L{Action}.

    @param fields: Additional fields to add to the start message.

    @return: A new L{Action}.
    """
    action = Action(logger, unicode(uuid4()), TaskLevel(level=[]), action_type,
                    _serializers)
    action._start(fields)
    return action


class TooManyCalls(Exception):
    """
    The callable was called more than once.

    This typically indicates a coding bug: the result of
    C{preserve_context} should only be called once, and
    C{preserve_context} should therefore be called each time you want to
    pass the callable to a thread.
    """


def preserve_context(f):
    """
    Package up the given function with the current Eliot context, and then
    restore context and call given function when the resulting callable is
    run. This allows continuing the action context within a different thread.

    The result should only be used once, since it relies on
    L{Action.serialize_task_id} whose results should only be deserialized
    once.

    @param f: A callable.

    @return: One-time use callable that calls given function in context of
        a child of current Eliot action.
    """
    action = currentAction()
    if action is None:
        return f
    task_id = action.serialize_task_id()
    called = threading.Lock()

    def restore_eliot_context(*args, **kwargs):
        # Make sure the function has not already been called:
        if not called.acquire(False):
            raise TooManyCalls(f)

        with Action.continue_task(task_id=task_id):
            return f(*args, **kwargs)
    return restore_eliot_context
