What's New
==========

0.4.0
^^^^^

Note that this is the last release that will make incompatible changes without interim deprecation warnings.


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


