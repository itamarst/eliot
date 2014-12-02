Logging Across Processes and Threads
====================================

Introduction
------------

In many applications we are interested in tasks that exist in more than just a single thread or in a single process.
For example, one server may send a request to another server over a network and we would like to trace the combined operation across both servers' logs.
To make this as easy as possible Eliot supports serializing task identifiers for transfer over the network (or between threads), allowing tasks to span multiple processes.


.. _cross process tasks:

Cross-Process Tasks
-------------------

``eliot.Action.serialize_task_id()`` can be used to create some ``bytes`` identifying a particular location within a task.
``eliot.Action.continue_task()`` converts a serialized task identifier into an ``eliot.Action`` and then starts the ``Action``.
The process which created the task serializes the task identifier and sends it over the network to the process which will continue the task.
This second process deserializes the identifier and uses it as a context for its own messages.

In the following example the task identifier is added as a header to a HTTP request:

.. literalinclude:: ../../examples/cross_process_client.py

The server that receives the request then extracts the identifier:

.. literalinclude:: ../../examples/cross_process_server.py

Tracing logs across multiple processes makes debugging problems dramatically easier.
For example, let's run the following:

.. code-block:: shell

   $ python examples/cross_process_server.py &
   $ python examples/cross_process_client.py 5 0

Here's what the combined logs from the client and server might look like when sorted by ``task_level`` and formatted to be more readable::

    process='client' task_uuid='40be6df2' task_level='/1' action_type='main'
        action_status='started'

    process='client' task_uuid='40be6df2' task_level='/2/1' action_type='http_request'
        action_status='started' x=5 y=0

    process='server' task_uuid='40be6df2' task_level='/2/2/1' action_type='eliot:remote_task'
        action_status='started'

    process='server' task_uuid='40be6df2' task_level='/2/2/2/1' action_type='divide'
        action_status='started' x=5 y=0

    process='server' task_uuid='40be6df2' task_level='/2/2/2/2' action_type='divide'
        action_status='failed' exception='exceptions.ZeroDivisionError' reason='integer division or modulo by zero'

    process='server' task_uuid='40be6df2' task_level='/2/2/3' action_type='eliot:remote_task'
        action_status='failed' exception='exceptions.ZeroDivisionError' reason='integer division or modulo by zero'

    process='client' task_uuid='40be6df2' task_level='/2/3' action_type='http_request'
       action_status='failed' exception='requests.exception.HTTPError' reason='500 Server Error: INTERNAL SERVER ERROR'

    process='client' task_uuid='40be6df2' task_level='/3' action_type='main'
       action_status='failed' exception='requests.exception.HTTPError' reason='500 Server Error: INTERNAL SERVER ERROR'

The reason the client received a 500 error code is completely obvious in these logs.


Cross-Thread Tasks
------------------

``eliot.Action`` objects should only be used on the thread that created them.
If you want your task to span multiple threads use the API described above.


Ensuring Message Uniqueness
---------------------------

Serialized task identifiers should be used at most once.
For example, every time a remote operation is retried a new call to ``serialize_task_id()`` should be made to create a new identifier.
Otherwise there is a chance that you will end up with messages that have duplicate identification (i.e. two messages with matching ``task_uuid`` and ``task_level`` values), making it more difficult to trace causality.

If this is not possible you may wish to start a new Eliot task upon receiving a remote request, while still making sure to log the serialized remote task identifier.
The inclusion of the remote task identifier will allow manual or automated reconstruction of the cross-process relationship between the original and new tasks.

Another alternative in some cases is to rely on unique process or thread identity to distinguish between the log messages.
For example if the same serialized task identifier is sent to multiple processes, log messages within the task can still have a unique identity if a process identifier is included with each message.


Logging Output for Multiple Processes
-------------------------------------

If logs are being combined from multiple processes an identifier indicating the originating process should be included in log messages.
This can be done a number of ways, e.g.:

* Have your destination add another field to the output.
* Rely on Logstash, or whatever your logging pipeline tool is, to add a field when shipping the logs to your centralized log store.
