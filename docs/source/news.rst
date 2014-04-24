What's New
==========

0.4.0
^^^^^

Incompatible changes from 0.3.0:

* ``Logger`` no longer does JSON serialization; it's up to destinations to decide how to serialize the dictionaries they receive.
* ``ActionType`` no longer supports defining additional failure fields, and therefore accepts one argument less.

Features:

* Added support for Python 3.3.
* Actions can now be explicitly finished using a public API: ``Action.finish()``.
