.. _python2:

Python 2.7 Support
==================

Eliot supports Python 2.7 as of release 1.16.
However, Eliot will drop support for Python 2 in an upcoming release (probably 1.17 or 1.18).

If you are using Eliot with Python 2, keep the following in mind:

* I will provide critical bug fixes for Python 2 for one year after the last release supporting Python 2.7.
  I will accept patches for critical bug fixes after that (or you can pay me to do additional work).
* Make sure you use an up-to-date ``setuptools`` and ``pip``; in theory this should result in only downloading versions of the package that support Python 2.
* For extra safety, you can pin Eliot in ``setup.py`` or ``requirements.txt`` by setting: ``eliot < 1.17``.

For example, if it turns out 1.16 is the last version that supports Python 2:

* 1.17 will only support Python 3.
* Critical bug fixes for Python 2 will be released as 1.16.1, 1.16.2, etc..

I will update this page once I know the final release where Python 2 is supported.
