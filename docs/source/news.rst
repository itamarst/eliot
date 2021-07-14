What's New
==========

Unreleased
^^^^^^^^^^

Features:

* ``Action.continue_task`` now takes ``action_task`` and extra fields to use for the action, so the default ``eliot:remote_task`` can be changed.

1.13.0
^^^^^^

Features:

* ``@capture_logging`` and ``MemoryLogger`` now support specifying a custom JSON encoder. By default they now use Eliot's encoder. This means tests can now match the encoding used by a ``FileDestination``.
* Added support for Python 3.9.

Deprecation:

* Python 3.5 is no longer supported.

1.12.0
^^^^^^

Features:

* Dask support now includes support for tracing logging of ``dask.persist()``, via wrapper API ``eliot.dask.persist_with_trace()``.

Bug fixes:

* Dask edge cases that previously weren't handled correctly should work better.

1.11.0
^^^^^^

Features:

* ``Message.log()`` has been replaced by top-level function ``log_message()``. Or if you're in the context of action ``ctx``, you can call ``ctx.log()``. See :ref:`messages` for details.
* Python 3.8 is now supported.
* The ``eliot-prettyprint`` command line tool now supports a more compact format by using the ``--compact`` argument.
* The ``eliot-prettyprint`` command line tool now supports outputting in local timezones using the ``--local-timezone`` argument.

1.10.0
^^^^^^

Bug fixes:

* ``@eliot.testing.capture_logging`` now passes ``*args`` and ``**kwargs`` to the wrapped function, as one would expect. Fixes #420. Thanks to Jean-Paul Calderone for the bug report.
* Eliot works with Dask 2.0. Thanks to Dan Myung for the bug report.

1.9.0
^^^^^

Deprecation:

* Python versions older than 3.5.3, e.g. the 3.5.2 on Ubuntu Xenial, don't work with Eliot, so added a more informative error message explaining that. Fixes #418. Thanks to Richard van der Hoff for the bug report.

Features:

* If you call ``to_file()/FileDestination()`` with a non-writable file, an
  exception will be raised. This prevents logging from being silently swallowed
  when the program runs. Fixes #403.
* PyPy3 is now officially supported.

Changes:

* If you log a NumPy array whose size > 10000, only a subset will logged. This is to ensure logging giant arrays by mistake doesn't impact your software's performance. If you want to customize logging of large arrays, see :ref:`large_numpy_arrays`. Fixes #410.

1.8.0
^^^^^

Features:

* Eliot now supports Trio coroutines, as well as other frameworks that utilize Python 3.7's ``contextvars`` (Python 3.5 and 3.6 are also supported, using backport packages).

Deprecation:

* ``eliot.use_asyncio_context()`` is no longer necessary.
  On Python 3.5 and 3.6, however, you should make sure to import ``eliot`` (or ``aiocontextvars``) before you start your first event loop.

Changes:

* Python 2.7 is now in legacy support mode; the last major Eliot release supporting it is 1.7.0.
  See :ref:`python2` for details.
* Python 3.4 is no longer supported.

1.7.0
^^^^^

Documentation:

* Eliot has an API for testing that your logs were output correctly. Until now, however, the documentation was overly focused on requiring usage of types, which are optional, so it has been rewritten to be more generic: :doc:`read more about the testing API here<generating/testing>`.

Features:

* Generating messages is much faster.
* Eliot now works with PyInstaller. Thanks to Jean-Paul Calderone for the bug report. Fixes issue #386.
* The testing infrastructure now has slightly more informative error messages. Thanks to Jean-Paul Calderone for the bug report. Fixes issue #373.
* Added lower-level testing infrastructure—``eliot.testing.swap_logger`` and ``eliot.testing.check_for_errors``—which is useful for cases when the ``@capture_logging`` decorator is insufficient. For example, test methods that are async, or return Twisted ``Deferred``. See the :doc:`testing documentation<generating/testing>` for details. Thanks to Jean-Paul Calderone for the feature request. Fixes #364.
* ``eliot.ValidationError``, as raised by e.g. ``capture_logging``, is now part of the public API. Fixed issue #146.

Twisted-related features:

* New decorator, ``@eliot.twisted.inline_callbacks`` , which is like Twisted's ``inlineCallbacks`` but which also manages the Eliot context. Thanks to Jean-Paul Calderone for the fix. Fixed issue #259.
* ``eliot.twisted.DeferredContext.addCallbacks`` now supports omitting the errback, for compatibility with Twisted's ``Deferred``. Thanks to Jean-Paul Calderone for the fix. Fixed issue #366.

Bug fixes:

* Fixed bug in the ``asyncio`` coroutine support where only the thread where ``use_asyncio_context()`` was called supported coroutine-specific contexts. Fixes issue #388.
* ``ILogger.write`` is now explicitly thread-safe. The ``MemoryLogger`` (as used
  by tests) implementation of this method which was previously not thread-safe
  is now thread-safe. Thanks to Jean-Paul Calderone for the patch. Fixes issue
  #382.


1.6.0
^^^^^

Deprecation:

* Python 2 is still supported, but will be dropped in one of the next releases. See :ref:`python2`.

Features:

* NumPy integers, floats, bools and arrays are now automatically serialized to JSON, via a new default JSON encoder (``eliot.json.EliotJSONEncoder``).
* Dask support: replace ``dask.compute()`` with ``eliot.dask.compute_with_trace()`` to automatically preserve Eliot context for ``Bag`` and ``Delayed`` Dask computations. See :ref:`dask_usage` for details.
* New decorator, ``@eliot.log_call``, which automatically creates an action that starts when function is called and ends when it returns. See :ref:`log_call decorator`.
* A parser library for parsing serialized Eliot JSON messages into a tree of Python objects. See :ref:`parsing_logs` for details.

Testing features:

* ``eliot.testing.LoggedAction`` has a new method, ``type_tree()``, that returns the tree of action and message types.
  This allows for easier testing of action structure.
* ``eliot.testing.LoggedAction.of_type`` now accepts the type as a string, not just an ``eliot.ActionType`` instance.
  Similarly, ``LoggedMessage.of_type`` also accepts the type as a string.

1.5.0
^^^^^

Bug fixes:

* The standard library ``logging`` bridge now logs tracebacks, not just messages.

Features:

* You can now pass in an explicit traceback tuple to ``write_traceback``.

Changes:

* The deprecated ``system`` argument to ``write_traceback`` and ``writeFailure`` has been removed.

1.4.0
^^^^^

Features:

* Added support for routing standard library logging into Eliot; see :ref:`migrating` for details.
* Added support for Python 3.7.

Output format changes:

* All messages now have either ``message_type`` or ``action_type`` fields.

Documentation:

* Documented how to add log levels, and how to filter Eliot logs.
* Logstash configuration is closer to modern version's options, though still untested.
* Explained how to integrate/migrate existing logging with Eliot.

1.3.0
^^^^^

Features:

* The default JSON output format now supports custom JSON encoders. See :ref:`custom_json` for details.
  Thanks to Jonathan Jacobs for feedback.

Bug fixes:

* ``MemoryLogger.validate()`` now gives more informative errors if JSON encoding fails.
  Thanks to Jean-Paul Calderone for the bug report.

Deprecations:

* On Python 3, the JSON encoder used by ``to_file`` and ``FileDestination`` would accept ``bytes``... sometimes.
  This is deprecated, and will cease to work in a future release of Eliot (on Python 3, it will continue to work on Python 2).
  If you wish to include ``bytes`` in JSON logging, convert it to a string in the log-generating code, use Eliot's type system, or use a custom JSON encoder.

1.2.0
^^^^^

Features:

* Eliot now does the right thing for ``asyncio`` coroutines in Python 3.5 and later.
  See :ref:`asyncio_coroutine` for details.
  Thanks to x0zzz for the bug report.

Misc:

* ``Action.continue_task`` can now accept text task IDs (``str`` in Python 3, ``unicode`` in Python 2).

1.1.0
^^^^^

Features:

* Messages are no longer lost if they are logged before any destinations are added.
  In particular, messages will be buffered in memory until the first set of destinations are added, at which point those messages will be delivered.
  Thanks to Jean-Paul Calderone for the feature request.
* ``eliot.add_destinations`` replaces ``eliot.add_destination``, and accepts multiple Destinations at once.
* ``eliot.twisted.TwistedDestination`` allows redirecting Eliot logs to ``twisted.logger``.
  Thanks to Glyph Lefkowitz for the feature request.

Misc:

* Coding standard switched to PEP-8.
* Dropped support for Python 3.3.
* Dropped support for versions of Twisted older than 15.2 (or whenever it was that ``twisted.logger`` was introduced).
* Dropped support for ``ujson``.

1.0.0
^^^^^

Eliot is stable, and has been for a while, so switching to v1.0.

Features:

* New API: ``MessageType.log()``, the equivalent of ``Message.log()``, allows you to quickly create a new typed log message and write it out.
* New APIs: ``eliot.current_action()`` returns the current ``Action``, and ``Action.task_uuid`` is the task's UUID.
* You can now do ``with YOUR_ACTION().context() as action:``, i.e. ``Action.context()`` context manager returns the ``Action`` instance.
* ``ActionType.as_task`` no longer requires a logger argument, matching the other APIs where passing in a logger is optional.

0.12.0
^^^^^^

Features:

* Python 3.6 support.

Misc:

* Made test suite pass again with latest Hypothesis release.

0.11.0
^^^^^^

Features:

* Eliot tasks can now more easily :ref:`span multiple threads <cross thread tasks>` using the new ``eliot.preserve_context`` API.
* ``eliot-prettyprint`` command line tool now pretty prints field values in a more informative manner.

Bug fixes:

* ``eliot-prettyprint`` now handles unparseable lines by skipping formatting them rather than exiting.

0.10.1
^^^^^^

Bug fixes:

* Fixed regression in 0.10.0: fix validation of failed actions and tracebacks with extracted additional fields.

0.10.0
^^^^^^

Features:

* ``register_exception_extractor`` allows for more useful :ref:`logging of failed actions and tracebacks<extract errors>` by extracting additional fields from exceptions.
* Python 3.5 support.

Bug fixes:

* Journald support works on Python 3.


0.9.0
^^^^^

Features:

* Native :ref:`journald support<journald>`.
* ``eliot-prettyprint`` is a command-line tool that formats JSON Eliot messages into a more human-friendly format.
* ``eliot.logwriter.ThreadedWriter`` is a Twisted non-blocking wrapper for any blocking destination.

0.8.0
^^^^^

Features:

* ``Message.log`` will log a new message, combining the existing ``Message.new`` and ``Message.write``.
* ``write_traceback`` and ``writeFailure`` no longer require a ``Logger``; they now default to using the global one.
* The logs written with ``redirectLogsForTrial`` are now written in JSON format, rather than with ``pformat``.

Bug fixes:

* ``FileDestination`` will now call ``flush()`` on the given file object after writing the log message.
  Previously log messages would not end up being written out until the file buffer filled up.
* Each ``Message`` logged outside the context of an action now gets a unique ``task_id``.


0.7.0
^^^^^

* Creating your own ``Logger`` instances is no longer necessary; all relevant APIs now default to using a global one.
  A new testing decorator (``eliot.testing.capture_logging``) was added to capture global logging.
* Support positional ``Field``-instance arguments to ``fields()`` to make combining existing field types and simple fields more convenient.
  Contributed by Jonathan Jacobs.
* ``write_traceback`` and ``writeFailure`` no longer require a ``system`` argument, as the combination of traceback and action context should suffice to discover the origin of the problem.
  This is a minor change to output format as the field is also omitted from the resulting ``eliot:traceback`` messages.
* The ``validate_logging`` testing utility now skips validation when the decorated test method raises ``SkipTest``.
* Exceptions in destinations are now handled better: instead of being dropped silently an attempt is made to log a message about the problem.
  If that also fails then the exception is dropped.


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
