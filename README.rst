Eliot: Logging as Storytelling
==============================

Eliot provides a structured logging and tracing system for Python that generates log messages describing a forest of nested actions.
Actions start and eventually finish, successfully or not.
Log messages thus tell a story: what happened and what caused it.

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
* Excellent support for unit testing your logging code.
* Emphasis on performance, including no blocking I/O in logging code path.
* Optional Twisted support.
* Designed for JSON output, usable by Logstash/Elasticsearch.
* Supports CPython 2.7, 3.3 and PyPy.

Eliot is released by `HybridCluster`_ under the Apache 2.0 License.

To install::

     $ pip install eliot

Downloads are available on `PyPI`_.

Documentation can be found on `Read The Docs`_.

Bugs and feature requests should be filed at the project `Github page`_.

.. _Read the Docs: https://eliot.readthedocs.org/
.. _Github page: https://github.com/hybridcluster/eliot
.. _PyPI: https://pypi.python.org/pypi/eliot
.. _HybridCluster: https://hybridcluster.github.io

.. image:: https://travis-ci.org/hybridcluster/eliot.png?branch=master
           :target: http://travis-ci.org/hybridcluster/eliot
           :alt: Build Status
