Twisted Support
===============

Eliot provides a variety of APIs to support integration with the `Twisted`_ networking framework.

.. _Twisted: https://twistedmatrix.com


Destinations
------------

``eliot.logwriter.ThreadedFileWriter`` is a logging destination that writes to a file-like object in a thread.
This is useful because it keeps the Twisted thread from blocking if writing to the log file is slow.
``ThreadedFileWriter`` is a Twisted ``Service`` and starting it will call ``add_destination`` for you and stopping it will call ``remove_destination``; there is no need to call those directly.

.. literalinclude:: ../../examples/logfile.py

If you want log rotation you can pass in one of the classes from `twisted.python.logfile`_ as the destination file.

.. _twisted.python.logfile: https://twistedmatrix.com/documents/current/api/twisted.python.logfile.html

If you're using Twisted's ``trial`` program to run your tests you can redirect your Eliot logs to Twisted's logs by calling ``eliot.twisted.redirectLogsForTrial()``.
This function will automatically detect whether or not it is running under ``trial``.
If it is then you will be able to read your Eliot logs in ``_trial_temp/test.log``, where ``trial`` writes out logs by default.
If it is not running under ``trial`` it will not do anything.
In addition calling it multiple times has the same effect as calling it once.
As a result you can simply call it in your package's ``__init__.py`` and rely on it doing the right thing.
Take care if you are separately redirecting Twisted logs to Eliot; you should make sure not to call ``redirectLogsForTrial`` in that case so as to prevent infinite loops.


Logging Failures
----------------

``eliot.writeFailure`` is the equivalent of ``eliot.write_traceback``, only for ``Failure`` instances:

.. code-block:: python

    from eliot import Logger, writeFailure

    class YourClass(object):
        logger = Logger()

        def run(self):
            d = dosomething()
            d.addErrback(writeFailure, self.logger, u"yourapp:yourclass")
