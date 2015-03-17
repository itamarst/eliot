Message Fields in Depth
=======================

Built-in Fields
---------------

A number of fields are reserved by Eliot's built-in message structure and should not be added to messages you create.

.. _task fields:

Task Fields
^^^^^^^^^^^

The following fields are present in all messages.
Each message is uniquely identified by the combined values in these fields.

* ``task_uuid``: The task (top-level action) this message is part of.
* ``task_level``: The specific location of this message within the task's tree of actions.
  For example, ``[3, 2, 4]`` indicates the message is the 4th child of the 2nd child of the 3rd child of the task.

Consider the following code sample:

.. code-block:: python

     from eliot import start_action, Logger, Message

     logger = Logger()

     with start_action(logger, u"parent"):
         Message.new(x="1").write(logger)
         with start_action(logger, u"child"):
             Message.new(x="2").write(logger)

If you sort the resulting messages by their ``task_level`` you will get the tree of messages:

* ``task_level=[1] action_type="parent" action_status="started"``
* ``task_level=[2] x="1"``

    * ``task_level=[3, 1] action_type="child" action_status="started"``
    * ``task_level=[3, 2] x="2"``
    * ``task_level=[3, 3] action_type="child" action_status="finished"``

* ``task_level=[4] action_type="parent" action_status="finished"``


Other Built-In Fields
^^^^^^^^^^^^^^^^^^^^^

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
