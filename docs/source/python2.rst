.. _python2:

Python 2.7 Support
==================

The last version of Eliot to support Python 2.7 was release 1.7.

If you are using Eliot with Python 2, keep the following in mind:

* I will provide critical bug fixes for Python 2 until March 2020.
  I will accept patches for critical bug fixes after that (or you can `pay for my services <https://pythonspeed.com/services/#eliot>`_ to do additional work).
* Make sure you use an up-to-date ``setuptools`` and ``pip``; in theory this should result in only downloading versions of the package that support Python 2.
* For extra safety, you can pin Eliot in ``setup.py`` or ``requirements.txt`` by setting: ``eliot < 1.8``.
* Critical bug fixes for Python 2 will be released as 1.7.1, 1.7.2, etc..
