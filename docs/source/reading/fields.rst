Message Fields in Depth
=======================

Structure
---------

Eliot messages are typically serialized to JSON objects.
Fields therefore must have ``str`` as their name.
Message values must be supported by JSON: ``int``, ``float``, ``None``, ``str``, ``dict`` or ``list``.
The latter two can only be composed of other supported types.

Built-in Fields
---------------

A number of fields are reserved by Eliot's built-in message structure and should not be added to messages you create.

All messages contain ``task_uuid`` and ``task_level`` fields.
Each message is uniquely identified by the combined values in these fields.
For more information see the :ref:`actions and tasks <task fields>` documentation.

In addition, the following field will also be present:

* ``timestamp``: Number of seconds since Unix epoch as a ``float`` (the output of ``time.time()``).
  Since system time may move backwards and resolution may not be high enough this cannot be relied on for message ordering.

Every logged message will have either ``message_type`` or ``action_type`` fields depending whether they originated as a standalone message or as the start or end of an action.
Present in regular messages:

* ``message_type``: The type of the message, e.g. ``"yourapp:yoursubsystem:yourmessage"``.

Present in action messages:

* ``action_type``: The type of the action, e.g. ``"yourapp:yoursubsystem:youraction"``.
* ``action_status``: One of ``"started"``, ``"succeeded"`` or ``"failed"``.

The following fields can be added to your messages, but should preserve the same meaning:

* ``exception``: The fully qualified Python name (i.e. import path) of an exception type, e.g. ``"yourpackage.yourmodule.YourException"``.
* ``reason``: A prose string explaining why something happened. Avoid usage if possible, better to use structured data.
* ``traceback``: A string with a traceback.


User-Created Fields
-------------------

It is recommended, but not necessary (and perhaps impossible across organizations) that fields with the same name have the same semantic content.
