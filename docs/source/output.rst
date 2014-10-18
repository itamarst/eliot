Destinations: Outputting Logs
=============================

Destinations are how messages get written out by the ``Logger`` class.
A destination is a callable that takes a message dictionary.
For example, if we want to write out a JSON message per line we can do:

.. code-block:: python

    import json, sys
    from eliot import add_destination

    def stdout(message):
        sys.stdout.write(json.dumps(message) + b"\n")
    add_destination(stdout)


Outputting to Files
-------------------

 ``eliot.to_file`` adds a destination that logs a JSON message per line to a file.
For example:

.. code-block:: python

    from eliot import to_file
    to_file(open("eliot.log", "ab"))

Note that this destination is blocking: if writing to a file takes a long time your code will not be able to proceed until writing is done.
