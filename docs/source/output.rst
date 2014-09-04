Destinations: Outputting Logs
=============================

Destinations are how messages get written out by the ``Logger`` class.
A destination is a callable that takes a message dictionary.
For example, if we want to write out a JSON message per line we can do:

.. code-block:: python

    import json
    from eliot import add_destination

    def stdout(message):
        sys.stdout.write(json.dumps(message) + b"\n")
    add_destination(stdout)
