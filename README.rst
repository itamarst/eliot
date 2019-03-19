Eliot: Logging that tells you *why* it happened
================================================

.. image:: https://travis-ci.org/itamarst/eliot.png?branch=master
           :target: http://travis-ci.org/itamarst/eliot
           :alt: Build Status

Python's built-in ``logging`` and other similar systems output a stream of factoids: they're interesting, but you can't really tell what's going on.

* Why is your application slow?
* What caused this code path to be chosen?
* Why did this error happen?

Standard logging can't answer these questions.

But with a better model you could understand what and why things happened in your application.
You could pinpoint performance bottlenecks, you could understand what happened when, who called what.

That is what Eliot does.
``eliot`` is a Python logging system that outputs causal chains of **actions**: actions can spawn other actions, and eventually they either **succeed or fail**.
The resulting logs tell you the story of what your software did: what happened, and what caused it.

Eliot works well within a single process, but can also be used across multiple processes to trace causality across a distributed system.
Eliot is only used to generate your logs; you will still need tools like Logstash and ElasticSearch to aggregate and store logs if you are using multiple processes.

Eliot supports Python 3.4, 3.5, 3.6, 3.7 and PyPy.
2.7 is currently supported but will be dropped from future releases; see `here <https://eliot.readthedocs.io/en/stable/python2.html>`_ for details.
It is maintained by Itamar Turner-Trauring, and released under the Apache 2.0 License.

* `Read the documentation <https://eliot.readthedocs.io>`_.
* Download from `PyPI`_ or `conda-forge <https://anaconda.org/conda-forge/eliot>`_.
* Need help or have any questions? `File an issue <https://github.com/itamarst/eliot/issues/new>`_ on GitHub.
* **Commercial support** is available from `Python⇒Speed <https://pythonspeed.com/services/#eliot>`_.

Testimonials
------------

    "Eliot has made tracking down causes of failure (in complex external integrations and internal uses) tremendously easier. Our errors are logged to Sentry with the Eliot task UUID. That means we can go from a Sentry notification to a high-level trace of operations—with important metadata at each operation—in a few seconds. We immediately know which user did what in which part of the system."

    —Jonathan Jacobs

.. _Github: https://github.com/itamarst/eliot
.. _PyPI: https://pypi.python.org/pypi/eliot
