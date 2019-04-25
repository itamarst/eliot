Configuring Logging Output
==========================

You can register "destinations" to handle logging output; a destination is a callable that takes a message dictionary.
For example, if we want to just print each new message:

.. code-block:: python

    import json, sys
    from eliot import add_destinations

    def stdout(message):
        print(message)
    add_destinations(stdout)

Before destinations are added
-----------------------------

Up to a 1000 messages will be buffered in memory until the first set of destinations are added, at which point those messages will be delivered to newly added set of destinations.
This ensures that no messages will be lost if logging happens during configuration but before a destination is added.


Outputting JSON to a file
-------------------------

Since JSON is a common output format, Eliot provides a utility class that logs to a file, ``eliot.FileDestination(file=yourfile)``.
Each Eliot message will be encoded in JSON and written on a new line.
As a short hand you can call ``eliot.to_file``, which will create the destination and then add it automatically.
For example:

.. code-block:: python

    from eliot import to_file
    to_file(open("eliot.log", "ab"))

.. note::

    This destination is blocking: if writing to a file takes a long time your code will not be able to proceed until writing is done.
    If you're using Twisted you can wrap a ``eliot.FileDestination`` with a non-blocking :ref:`eliot.logwriter.ThreadedWriter<ThreadedWriter>`.
    This allows you to log to a file without blocking the Twisted ``reactor``.

.. _custom_json:

Customizing JSON Encoding
-------------------------

If you're using Eliot's JSON output you may wish to customize encoding.
By default Eliot uses ``eliot.json.EliotJSONEncoder`` (a subclass of ``json.JSONEncoder``) to encode objects.
You can customize encoding by passing a custom subclass to either ``eliot.FileDestination`` or ``eliot.to_file``:

.. code-block:: python

   from eliot.json import EliotJSONEncoder
   from eliot import to_file


   class MyClass:
       def __init__(self, x):
           self.x = x

   class MyEncoder(EliotJSONEncoder):
       def default(self, obj):
           if isinstance(obj, MyClass):
               return {"x": obj.x}
           return EliotJSONEncoder.default(self, obj)

   to_file(open("eliot.log", "ab"), encoder=MyEncoder)   

For more details on JSON encoding see the Python `JSON documentation <https://docs.python.org/3/library/json.html>`_.

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

You should call ``add_global_fields`` before ``add_destinations`` to ensure all messages get the global fields.
