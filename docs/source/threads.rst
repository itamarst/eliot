Logging Across Processes and Threads
====================================

Introduction
------------

In many applications we are interested in tasks that exist in more than just a single thread or in a single process.
For example, one server may send a request to another server over a network and we would like to trace the combined operation across both servers' logs.
To make this as easy as possible Eliot supports serializing task identifiers for transfer over the network (or between threads), allowing tasks to span multiple processes.


Cross-Process Tasks
-------------------

``eliot.Action.serialize_task_id()`` can be used to create some ``bytes`` identifying a particular location within a task.
``eliot.Action.deserialize()`` is a context manager that converts a serialized task identifier into an ``eliot.Action``.
The process which created the task serializes the task identifier and sends it over the network to the process which will continue the task.
This second process deserializes the identifier and uses it as a context for its own messages.

In the following example the task identifier is added as a header to a HTTP request:

The server that receives the request then extracts the identifier:

Here's what the combined logs look like:


Cross-Thread Tasks
------------------

``eliot.Action`` objects should only be used on the thread that created them.
If you want your task to span multiple threads use the API described above.


Serialized Tasks Should Only Be Used Once
-----------------------------------------

Every time a remote operation is retried a new ``Action`` should be started and serialized along with the operation.
Otherwise there is a chance that you will end up with messages that have duplicate identification (i.e. two messages with matching ``task_uuid`` and ``task_level`` values), making it more difficult to trace causality.

More generally you should make sure a serialized task identifier is only used once.
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
