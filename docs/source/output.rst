Configuring Logging Output
==========================

Destinations are how messages get written out by the ``Logger`` class.
A destination is a callable that takes a message dictionary.
For example, if we want each message to be encoded in JSON and written on a new line on stdout:

.. code-block:: python

    import json, sys
    from eliot import add_destination

    def stdout(message):
        sys.stdout.write(json.dumps(message) + b"\n")
    add_destination(stdout)


Outputting to Files
-------------------

``eliot.to_file`` adds a destination that logs to a file.
Each Eliot message will be encoded in JSON and written on a new line.
For example:

.. code-block:: python

    from eliot import to_file
    to_file(open("eliot.log", "ab"))

.. note::

    This destination is blocking: if writing to a file takes a long time your code will not be able to proceed until writing is done.
    If you're using Twisted you can use the non-blocking :ref:`eliot.logwriter.ThreadedFileWriter<ThreadedFileWriter>` to log to a file.
