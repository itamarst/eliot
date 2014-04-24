What's New
==========

0.4.0
^^^^^

Incompatible changes from v0.3:

* ``ActionType`` no longer supports defining additional failure fields, and therefore accepts one argument less.

Features:

* Added support for Python 3.3.
* Actions can now be explicitly finished using a public API: ``Action.finish()``.
* ``Action.context()`` context manager allows setting an action context without finishing the action when exiting the block.
