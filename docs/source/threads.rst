Thread Safety
=============

Eliot will be thread-safe, but work still needs to be done to ensure this.
Particular issues are discussed below.


``eliot.Action``
----------------
``eliot.Action`` objects should only be used on the thread that created them.
This means that currently it is not possible to have a task that involves multiple threads.
In the future there will be an API for extracting and setting task identity that will allow this, as well as transmitting this information to other processes for cross-process tasks.
