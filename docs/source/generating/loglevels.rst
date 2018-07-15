Log Levels
==========

Eliot does not have a native set of logging levels, as some systems do.
It does distinguish between normal log messages and errors—failed actions and tracebacks can both be considered as errors.

However, you can add log levels yourself.


Generating messages with log levels
-----------------------------------

All you need to do to add a log level is just add an appropriate field to your logging, for example:

.. code-block:: python

     from eliot import start_action

     with start_action(action_type=u"store_data", log_level="INFO"):
         x = get_data()
         store_data(x)


Choosing log levels
-------------------

In an excellent `article by Daniel Lebroro <https://labs.ig.com/logging-level-wrong-abstraction>`_, he explains that he chose the logging levels "for test environment", "for production environment", "investigate tomorrow", and "wake me in the middle of the night".
These seem rather more informative and useful than "INFO" or "WARN".

If you are implementing a service you will be running, consider choosing log levels that are meaningful on an organizational level.

