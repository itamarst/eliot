# parsing eliot actions


* don't want to care about how messages are serialized to log: JSON is
  irrevelant. want to operate at level of dicts

* want to "handle" receiving an arbitrary stream of messages in arbitrary order
  * from different tasks
  * out of order in the same task
  * messages without task ids
  * messages with task ids without task levels
  * some actions will never be completed
  * some tasks will be completed while some actions have not

* it's unclear when we'd want to emit tasks / actions / messages when handling
  a stream, given that we might not ever get results

* "tasks" are a special case of "actions": they are actions at the root

* `message_type` and `action_type` are fundamentally the same thing


## Data interfaces

### Message

* `timestamp` :: Unix timestamp
* `task_uuid` :: uuid4
* `task_level` :: `TaskLevel`
* `contents` :: dict of text -> unspecified data

### Action

* `start_time` :: Unix timestamp
* `end_time` :: Unix timestamp
* `duration` (== `end_time` - `start_time`) :: seconds
* `task_uuid` :: uuid4
* `task_level` :: `TaskLevel`
* `messages` :: list of messages / actions
* `status` :: "started" | "succeeded" | "finished"

### Task

As `Action`, except `task_level` will always be `TaskLevel([])`.

We might not even need a special class for this.


## Code interfaces

```
def add_message(action, message):
    """
    Add `message` to `action`.

    If `message` is a part of `action`, then insert it into the list of
    messages.

    @param action: A `WrittenAction`, or `None` if this is the first message
        received.
    @param message: A `WrittenMessage`

    @raise WrongTask: If `message` belongs to a different task
    @raise DuplicateMessage: If a different `message` has already been logged
        at the same task level.
    @raise WrongAction: If `message` belongs to the same task, but in a
        different part of the action tree. i.e. If `message` is not a child of
        action.

    @return: Updated `WrittedAction` object.
    """
```

* Name subject to variation
* Should probably just add message to appropriate action if message is a
  grandchild of `action`
* Probably have special version for tasks that cannot raise `WrongAction`
* Assumes `WrittenAction` is a `PClass`.

We'd then have a wrapper function for handling a stream of messages of any
task that would look like this:

```
def iter_tasks(messages, handle_error=None):
    """
    Turn a stream of logged messages into tasks.

    @param messages: An iterable of `WrittenMessage`
    @param handle_error: A unary callable that is called whenever we receive
        a corrupt message. If not specified, will just raise the exception.

    @yield: A stream of `WrittenAction` objects, each representing a top-level
        task.
    """
```

As currently specified, the only error that can be raised would be
`DuplicateMessage`.


### Alternative

We have Twisted-style event handling classes:

```
class MessageReceiver:

    def got_message(self, message):
        """
        Called when we receive a `WrittenMessage`.
        """

    def action_started(self, action):
        """
        Called when we receive a message that starts a `WrittenAction`.
        """

    def action_finished(self, action):
        """
        Called when we receive a message that finishes a `WrittenAction`.
        """

    def task_started(self, task):
        """
        Called when a top-level task has started.
        """

    def task_finished(self, task):
        """
        Called when a top-level task has finished.
        """

    def stream_ended(self):
```

We could then layer the other, simpler approach on top of this.

## Downsides

There's no good answer in this solution for the fact that messages can come
out-of-order *and* that we can receive more messages than we can fit in
memory.

I suspect this is an intrinsic problem, and that the "right" answer is to
provide for both "memory hungry but correct" and a "fast results but maybe
not so correct" options.
