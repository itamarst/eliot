.. _python2:

Python 2.7 Support
==================

Eliot supports Python 2.7 as of release 1.7.
However, Eliot will drop support for Python 2 in an upcoming release (probably 1.8 or 1.9).

If you are using Eliot with Python 2, keep the following in mind:

* I will provide critical bug fixes for Python 2 for one year after the last release supporting Python 2.7.
  I will accept patches for critical bug fixes after that (or you can `pay for my services <https://pythonspeed.com/services/#eliot>`_ to do additional work).
* Make sure you use an up-to-date ``setuptools`` and ``pip``; in theory this should result in only downloading versions of the package that support Python 2.
* For extra safety, you can pin Eliot in ``setup.py`` or ``requirements.txt`` by setting: ``eliot < 1.8``.

For example, if it turns out 1.18 is the last version that supports Python 2:

* 1.8 will only support Python 3.
* Critical bug fixes for Python 2 will be released as 1.8.1, 1.8.2, etc..

I will update this page once I know the final release where Python 2 is supported.
