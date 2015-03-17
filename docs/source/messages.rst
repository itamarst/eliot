Logging Messages and Tracebacks
===============================

Messages
--------

At its base, Eliot outputs structured messages composed of named fields.
Eliot messages are typically serialized to JSON objects.
Fields therefore can have Unicode names, so either ``unicode`` or ``bytes`` containing UTF-8 encoded Unicode.
Message values must be supported by JSON: ``int``, ``float``, ``None``, ``unicode``, UTF-8 encoded Unicode as ``bytes``, ``dict`` or ``list``.
The latter two can only be composed of other supported types.

A ``Message`` is written to a ``Logger``, whose purpose is to create scope for unit tests to validate only specific messages.
Typically you will create a ``Logger`` per top-level class you are testing.

.. code-block:: python

    from eliot import Message

    class YourClass(object):
        def run(self):
            # Create a message with two fields, "key" and "value":
            msg = Message.new(key=123, value=u"hello")
            # Write the message:
            msg.write()

More succinctly:

.. code-block:: python

    from eliot import Message

    class YourClass(object):
        def run(self):
            Message.write(key=123, value=u"hello")

You can also create a new ``Message`` from an existing one by binding new values.
New values will override ones on the base ``Message``, but ``bind()`` does not mutate the original ``Message``.

.. code-block:: python

      # This message has fields key=123, value=u"hello"
      msg = Message.new(key=123, value=u"hello")
      # And this one has fields key=123, value=u"other", extra=456
      msg2 = msg.bind(value=u"other", extra=456)


Tracebacks
----------

You can also log tracebacks when your code hits an unexpected exception:

.. code-block:: python

    from eliot import write_traceback

    class YourClass(object):

        def run(self):
            try:
                 dosomething()
            except:
                 write_traceback()
