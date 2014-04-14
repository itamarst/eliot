Fields
^^^^^^

Reserved Fields
---------------

The following fields are reserved by Eliot's built-in message structure and should not be added to messages you create:

These fields are present in all messages.
Each message is uniquely identified by the combined values in these fields.

* ``task_uuid``: The task this message is part of.
* ``task_level``: The level of the action this message is part of.
* ``action_counter``: The index of the message within the current action.

Present in non-action messages:
* ``message_type``: For non-action messages, the type of the message, e.g. ``"yourapp:yoursubsystem:yourmessage"``. Every message will have either ``message_type`` or ``action_type`` messages.

Present in action messages:
* ``action_type``: For action messages, the type of the action, e.g. ``"yourapp:yoursubsystem:youraction"``.
* ``action_status``: For action messages, one of ``"started"``, ``"succeeded"`` or ``"failed"``.

The following fields can be added to your messages, but should preserve the same meaning:

* ``exception``: The FQPN of an exception type, e.g. ``"yourpackage.yourmodule.YourException"``.
* ``reason``: A prose string explaining why something happened. Avoid usage if possible, better to use structured data.
* ``traceback``: A string with a traceback.
* ``system``: A string, a subsystem in your application, e.g. ``"yourapp:yoursubsystem"``.


User-Created Fields
-------------------

It is recommended, but not necessary (and perhaps impossible across organizations) that fields with the same name have the same semantic content.
