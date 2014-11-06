Message Fields in Depth
=======================

Built-in Fields
---------------

A number of fields are reserved by Eliot's built-in message structure and should not be added to messages you create.

The following fields are present in all messages.
Each message is uniquely identified by the combined values in these fields.

* ``task_uuid``: The task (top-level action) this message is part of.
* ``task_level``: The specific location of this message within the task's tree of actions.
  For example, ``"/3/2/4"`` indicates the message is the 4th child of the 2nd child of the 3rd child of the task.
  ``"/1"`` would be the start message of the root action, and ``"/3/2/1"`` would be the start message of the nested action.

In addition, the following field will also be present:

* ``timestamp``: Number of seconds since Unix epoch as a ``float`` (the output of ``time.time()``).
  Since system time may move backwards and resolution may not be high enough this cannot be relied on for message ordering.

Assuming you are using ``MessageType`` and ``ActionType`` every logged message will have either ``message_type`` or ``action_type`` fields depending whether they originated as a standalone message or as the start or end of an action.
Present in regular messages:

* ``message_type``: The type of the message, e.g. ``"yourapp:yoursubsystem:yourmessage"``.

Present in action messages:

* ``action_type``: The type of the action, e.g. ``"yourapp:yoursubsystem:youraction"``.
* ``action_status``: One of ``"started"``, ``"succeeded"`` or ``"failed"``.

The following fields can be added to your messages, but should preserve the same meaning:

* ``exception``: The fully qualified Python name (i.e. import path) of an exception type, e.g. ``"yourpackage.yourmodule.YourException"``.
* ``reason``: A prose string explaining why something happened. Avoid usage if possible, better to use structured data.
* ``traceback``: A string with a traceback.
* ``system``: A string, a subsystem in your application, e.g. ``"yourapp:yoursubsystem"``.


User-Created Fields
-------------------

It is recommended, but not necessary (and perhaps impossible across organizations) that fields with the same name have the same semantic content.
