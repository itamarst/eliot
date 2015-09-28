.. _journald:

Journald
========

``journald`` is the native logging system on Linux operating systems that use ``systemd`` with support for structured, indexed log storage.
Eliot provides native ``journald`` support, with the following features:

* The default message field (``MESSAGE``) stores the Eliot message as JSON.
* The ``ELIOT_TASK`` field stores the task UUID.
* The ``ELIOT_TYPE`` field stores the message or action type if available.
* Failed actions get priority 3 ("err") and tracebacks get priority 2 ("crit").


Generating logs
---------------

The following example demonstrates how to enable ``journald`` output.

.. literalinclude:: ../../examples/journald.py


Querying logs
-------------

The ``journalctl`` utility can be used to extract logs from ``journald``.
Useful options include ``--all`` which keeps long fields from being truncated and ``--output cat`` which only outputs the body of the ``MESSAGE`` field, i.e. the JSON-serialized Eliot message.

Let's generate some logs:

.. code-block:: shell

   $ python journald.py

We can find all messages with a specific type:

.. code-block:: shell

   $ sudo journalctl --all --output cat ELIOT_TYPE=inbetween | eliot-prettyprint
   32ab1286-c356-439d-86f8-085fec3b65d0@/1
   2015-09-23 21:26:37.972403Z
     message_type: inbetween

We can filter to those that indicate errors:

.. code-block:: shell

   $ sudo journalctl --all --output cat --priority=err ELIOT_TYPE=divide | eliot-prettyprint
   ce64eb77-bb7f-4e69-83f8-07d7cdaffaca@/2
   2015-09-23 21:26:37.972945Z
     action_type: divide
     action_status: failed
     exception: exceptions.ZeroDivisionError
     reason: integer division or modulo by zero

We can also search by task UUID, in which case ``eliot-tree`` can also be used to process the output:

.. code-block:: shell

   $ sudo journalctl --all --output cat ELIOT_TASK=ce64eb77-bb7f-4e69-83f8-07d7cdaffaca | eliot-tree
   ce64eb77-bb7f-4e69-83f8-07d7cdaffaca
   +-- divide@1/started
       |-- a: 10
       |-- b: 0
       `-- timestamp: 2015-09-23 17:26:37.972716
       +-- divide@2/failed
           |-- exception: exceptions.ZeroDivisionError
           |-- reason: integer division or modulo by zero
           `-- timestamp: 2015-09-23 17:26:37.972945
