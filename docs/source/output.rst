Configuring Logging Output
==========================

You can register "destinations" to handle logging output.
A destination is a callable that takes a message dictionary.
For example, if we want each message to be encoded in JSON and written on a new line on stdout:

.. code-block:: python

    import json, sys
    from eliot import add_destination

    def stdout(message):
        sys.stdout.write(json.dumps(message) + "\n")
    add_destination(stdout)


Outputting to Files
-------------------

You can create a destination that logs to a file by calling ``eliot.FileDestination(file=yourfile)``.
Each Eliot message will be encoded in JSON and written on a new line.
As a short hand you can call ``eliot.to_file`` which will create the destination and then add it.
For example:

.. code-block:: python

    from eliot import to_file
    to_file(open("eliot.log", "ab"))

.. note::

    This destination is blocking: if writing to a file takes a long time your code will not be able to proceed until writing is done.
    If you're using Twisted you can wrap a ``eliot.FileDestination`` with a non-blocking :ref:`eliot.logwriter.ThreadedWriter<ThreadedWriter>`.
    This allows you to log to a file without blocking the Twisted ``reactor``.


.. _add_global_fields:

Adding Fields to All Messages
-----------------------------

Sometimes you want to add a field to all messages output by your process, regardless of destination.
For example if you're aggregating logs from multiple processes into a central location you might want to include a field ``process_id`` that records the name and process id of your process in every log message.
Use the ``eliot.add_global_fields`` API to do so, e.g.:

.. code-block:: python

    import os, sys
    from eliot import add_global_fields

    add_global_fields(process_id="%s:%d" % (sys.argv[0], os.getpid()))
