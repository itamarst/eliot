Eliot: Logging for Complex & Distributed Systems
================================================

.. image:: https://travis-ci.org/ScatterHQ/eliot.png?branch=master
           :target: http://travis-ci.org/ScatterHQ/eliot
           :alt: Build Status

Eliot is a Python logging system that outputs causal chains of actions happening within and across process boundaries: a logical trace of the system's operation.
In particular, Eliot can be used to *generate* meaningful, useful logs; tools like Logstash and ElasticSearch are still necessary to aggregate and store logs.

Eliot was originally created by ClusterHQ and is maintained by Itamar Turner-Trauring and others, under the Apache 2.0 License.
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
* Supports CPython 2.7, 3.4, 3.5, 3.6 and PyPy.

Eliot is supported by 3rd party libraries like  `eliot-tree`_, `eliot-profiler`_, and `eliot-profiler-analysis`_.
A preliminary `JavaScript implementation`_ is also available.

.. _PEP 8: http://legacy.python.org/dev/peps/pep-0008/
.. _Twisted: https://twistedmatrix.com/documents/current/core/development/policy/coding-standard.html
.. _documentation: https://eliot.readthedocs.org/
.. _Github: https://github.com/ClusterHQ/eliot
.. _PyPI: https://pypi.python.org/pypi/eliot
.. _eliot-tree: https://github.com/jonathanj/eliottree
.. _eliot-profiler: https://github.com/jamespic/eliot-profiler
.. _eliot-profiler-analysis: https://github.com/jamespic/eliot-profiler-analysis
.. _JavaScript implementation: https://github.com/jonathanj/eliot.js
