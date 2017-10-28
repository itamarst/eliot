Eliot: Logging that tells you *why* it happened
================================================

.. image:: https://travis-ci.org/ScatterHQ/eliot.png?branch=master
           :target: http://travis-ci.org/ScatterHQ/eliot
           :alt: Build Status

Most logging systems tell you *what* happened in your application, whereas ``eliot`` also tells you *why* it happened.

``eliot`` is a Python logging system that outputs causal chains of **actions**: actions can spawn other actions, and eventually they either **succeed or fail**.
The resulting logs tell you the story of what your software did: what happened, and what caused it.

Eliot works well within a single process, but can also be used across multiple processes to trace causality across a distributed system.
Eliot is only used to generate your logs; you will still need tools like Logstash and ElasticSearch to aggregate and store logs if you are using multiple processes.

Eliot supports Python 2.7, 3.4, 3.5, 3.6 and PyPy. It is maintained by Itamar Turner-Trauring, and released under the Apache 2.0 License.

* `Read the documentation <https://eliot.readthedocs.io>`_.
* Download from `PyPI`_.
* File bugs at `Github`_.
* Need help? `File an issue <https://github.com/ScatterHQ/eliot/issues/new>`_ or join the ``#eliot`` IRC channel on ``irc.freenode.net`` 

Testimonials
------------

    "Eliot has made tracking down causes of failure (in complex external integrations and internal uses) tremendously easier. Our errors are logged to Sentry with the Eliot task UUID. That means we can go from a Sentry notification to a high-level trace of operations—with important metadata at each operation—in a few seconds. We immediately know which user did what in which part of the system."

    —Jonathan Jacobs

.. _Github: https://github.com/ClusterHQ/eliot
.. _PyPI: https://pypi.python.org/pypi/eliot
