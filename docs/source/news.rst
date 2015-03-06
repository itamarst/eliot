What's New
==========

0.7.0
^^^^^

* Support positional ``Field``-instance arguments to ``fields()`` to make combining existing field types and simple fields more convenient.
  Contributed by Jonathan Jacobs.
* ``write_traceback`` and ``writeFailure`` no longer require a ``system`` argument, as the combination of traceback and action context should suffice to discover the origin of the problem.
  This is a minor change to output format as the field is also omitted from the resulting ``eliot:traceback`` messages.

0.6.0
^^^^^

.. warning::

    Incompatible output format change! In previous versions the ordering of messages and actions was ambiguous and could not be deduced from out-of-order logs, and even where it was possible sorting correctly was difficult.
    To fix this the ``action_counter`` field was removed and now all messages can be uniquely located within a specific task by the values in an :ref:`improved task_level field <task fields>`.

Features:

* Eliot tasks can now :ref:`span multiple processes and threads <cross process tasks>`, allowing for easy tracing of actions in complex and distributed applications.
* :ref:`eliot.add_global_fields <add_global_fields>` allows adding fields with specific values to all Eliot messages logged by your program.
  This can be used to e.g. distinguish between log messages from different processes by including relevant identifying information.

Bug fixes:

* On Python 3 files that accept unicode (e.g. ``sys.stdout``) should now work.


0.5.0
^^^^^

Features:

* Added support for Python 3.4.
* Most public methods and functions now have underscore-based equivalents to the camel case versions, e.g. ``eliot.write_traceback`` and ``eliot.writeTraceback``, for use in PEP 8 styled programs.
  Twisted-facing APIs and pyunit assertions do not provide these additional APIs, as camel-case is the native idiom.
* ``eliot.to_file`` outputs log messages to a file.
* Documented how to load Eliot logging into ElasticSearch via Logstash.
* Documentation has been significantly reorganized.


0.4.0
^^^^^

Note that this is the last release that will make incompatible API changes without interim deprecation warnings.


Incompatible changes from 0.3.0:

* ``Logger`` no longer does JSON serialization; it's up to destinations to decide how to serialize the dictionaries they receive.
* Timestamps are no longer encoded in TAI64N format; they are now provided as seconds since the Unix epoch.
* ``ActionType`` no longer supports defining additional failure fields, and therefore accepts one argument less.
*  ``Action.runCallback`` and ``Action.finishAfter`` have been removed, as they are replaced by ``DeferredContext`` (see below).


Features:

* Added a simpler API (``fields()``) for defining fields for ``ActionType`` and ``MessageType``.
* Added support for Python 3.3.
* Actions can now be explicitly finished using a public API: ``Action.finish()``.
* ``Action.context()`` context manager allows setting an action context without finishing the action when exiting the block.
* Added a new API for Twisted ``Deferred`` support: ``eliot.twisted.DeferredContext``.
* ``eliot.twisted.redirectLogsForTrial`` will redirect Eliot logs to Twisted's logs when running under the ``trial`` test runner.
