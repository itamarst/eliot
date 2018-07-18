Errors and Exceptions
=====================


Exceptions and Tracebacks
-------------------------

If you are using actions you don't need to do anything special to log exceptions: if an exception is thrown within the context of an action and not caught, the action will be marked as failed and the exception will be logged with it.

If you get a completely unexpected exception you may wish to log a traceback to aid debugging:

.. code-block:: python

    from eliot import write_traceback

    class YourClass(object):

        def run(self):
            try:
                 dosomething()
            except:
                 write_traceback()


You can also pass in the output of ``sys.exc_info()``:

.. code-block:: python

    import sys
    from eliot import write_traceback

    write_traceback(exc_info=sys.exc_info())


.. _extract errors:

Custom Exception Logging
------------------------

By default both failed actions and tracebacks log the class and string-representation of the logged exception.
You can add additional fields to these messages by registering a callable that converts exceptions into fields.
If no extraction function is registered for a class Eliot will look for registered functions for the exception's base classes.

For example, the following registration means all failed actions that fail with a ``MyException`` will have a ``code`` field in the action end message, as will tracebacks logged with this exception:

.. code-block:: python

   class MyException(Exception):
       def __init__(self, code):
           self.code = code

   from eliot import register_exception_extractor
   register_exception_extractor(MyException, lambda e: {"code": e.code})

By default Eliot will automatically extract fields from ``OSError``, ``IOError`` and other subclasses of Python's ``EnvironmentError``.
