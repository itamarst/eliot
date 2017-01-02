Eliot: Logging for Complex & Distributed Systems
================================================

.. image:: https://coveralls.io/repos/ClusterHQ/eliot/badge.png?branch=master
           :target: https://coveralls.io/r/ClusterHQ/eliot
           :alt: Coveralls test coverage information

.. image:: https://travis-ci.org/ClusterHQ/eliot.png?branch=master
           :target: http://travis-ci.org/ClusterHQ/eliot
           :alt: Build Status

Eliot is a Python logging system that outputs causal chains of actions happening within and across process boundaries: a logical trace of the system's operation.

Eliot is released by `ClusterHQ`_ under the Apache 2.0 License.
Download from `PyPI`_, read the `documentation`_, file bugs at `Github`_.
Need help? Join the ``#eliot`` IRC channel on ``irc.freenode.net``.

To install::

     $ pip install eliot

Features:

* Structured, optionally-typed log messages and actions.
* Logged actions can span processes and threads.
* Excellent support for unit testing your code's logging.
* Optional Twisted support.
* Native journald support, easily usable by Logstash/Elasticsearch.
* Supports CPython 2.7, 3.3, 3.4, 3.5, 3.6 and PyPy.

.. _PEP 8: http://legacy.python.org/dev/peps/pep-0008/
.. _Twisted: https://twistedmatrix.com/documents/current/core/development/policy/coding-standard.html
.. _documentation: https://eliot.readthedocs.org/
.. _Github: https://github.com/ClusterHQ/eliot
.. _PyPI: https://pypi.python.org/pypi/eliot
.. _ClusterHQ: https://clusterhq.com
.. _eliot-tree: https://warehouse.python.org/project/eliot-tree/
