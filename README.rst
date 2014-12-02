Eliot: Logging as Storytelling
==============================

.. image:: https://coveralls.io/repos/ClusterHQ/eliot/badge.png?branch=master
           :target: https://coveralls.io/r/ClusterHQ/eliot
           :alt: Coveralls test coverage information

.. image:: https://travis-ci.org/ClusterHQ/eliot.png?branch=master
           :target: http://travis-ci.org/ClusterHQ/eliot
           :alt: Build Status

Eliot is a Python logging system designed for complex applications, especially distributed systems.
Eliot's structured logs are traces of the system's actions both within and across process boundaries.
Actions start and eventually finish, successfully or not.
Instead of isolated facts the log messages are thus a story: a series of causal events.

Here's what your logs might look like before using Eliot::

    Going to validate http://example.com/index.html.
    Started download attempted.
    Download succeeded!
    Missing <title> element in "/html/body".
    Bad HTML entity in "/html/body/p[2]".
    2 validation errors found!

After switching to Eliot you'll get a tree of messages with both message contents and causal relationships encoded in a structured format:

* ``{"action_type": "validate_page", "action_status": "started", "url": "http://example.com/index.html"}``

  * ``{"action_type": "download", "action_status": "started"}``
  * ``{"action_type": "download", "action_status": "succeeded"}``
  * ``{"action_type": "validate_html", "action_status": "started"}``

    * ``{"message_type": "validation_error", "error_type": "missing_title", "xpath": "/html/head"}``
    * ``{"message_type": "validation_error", "error_type": "bad_entity", "xpath": "/html/body/p[2]"}``

  * ``{"action_type": "validate_html", "action_status": "failed", "exception": "validator.ValidationFailed"}``

* ``{"action_type": "validate_page", "action_status": "failed", "exception": "validator.ValidationFailed"}``

Features:

* Structured, typed log messages.
* Ability to log actions, not just point-in-time information: log messages become a trace of program execution.
* Logged actions can span processes and threads.
* Excellent support for unit testing your code's logging.
* Emphasis on performance, including no blocking I/O in logging code path.
* Optional Twisted support.
* Designed for JSON output, usable by Logstash/Elasticsearch.
* Supports CPython 2.7, 3.3, 3.4 and PyPy.
* Eliot APIs provide both `PEP 8`_ style (e.g. ``write_traceback()``) and `Twisted`_ (e.g. ``writeTraceback()``) method and function names.
  The only exceptions are pyunit-style assertions (e.g. ``assertContainsFields()``) and Twisted-specific APIs since both use camelCase by default.

Eliot is released by `ClusterHQ`_ under the Apache 2.0 License.

To install::

     $ pip install eliot

Downloads are available on `PyPI`_.

Documentation can be found on `Read The Docs`_.

Bugs and feature requests should be filed at the project `Github page`_.

You can ask for help on IRC at the ``#eliot`` channel on ``irc.freenode.net``.

.. _PEP 8: http://legacy.python.org/dev/peps/pep-0008/
.. _Twisted: https://twistedmatrix.com/documents/current/core/development/policy/coding-standard.html
.. _Read the Docs: https://eliot.readthedocs.org/
.. _Github page: https://github.com/ClusterHQ/eliot
.. _PyPI: https://pypi.python.org/pypi/eliot
.. _ClusterHQ: https://clusterhq.com
