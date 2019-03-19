Eliot: Logging that tells you *why* it happened
================================================

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

* **Start here:** :doc:`Quickstart documentation <quickstart>`
* Need help or have any questions? `File an issue <https://github.com/itamarst/eliot/issues/new>`_ on GitHub.
* Commercial support is available from `Python⇒Speed<https://pythonspeed.com/services/#eliot`_.
* Read on for the full documentation.

Media
-----

`Podcast.__init__ episode 133 <https://www.podcastinit.com/eliot-logging-with-itamar-turner-trauring-episode-133/>`_ covers Eliot:

.. raw:: html

   <script class="podigee-podcast-player" src="https://cdn.podigee.com/podcast-player/javascripts/podigee-podcast-player.js" data-configuration="https://www.podcastinit.com/?podigee_player=390"></script>

Testimonials
------------

    "Eliot has made tracking down causes of failure (in complex external integrations and internal uses) tremendously easier. Our errors are logged to Sentry with the Eliot task UUID. That means we can go from a Sentry notification to a high-level trace of operations—with important metadata at each operation—in a few seconds. We immediately know which user did what in which part of the system."

    —Jonathan Jacobs

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :titlesonly:

   quickstart
   introduction
   news
   generating/index
   outputting/index
   reading/index
   usecases/index
   python2
   development


Project Information
-------------------

Eliot is maintained by `Itamar Turner-Trauring <mailto:itamar@itamarst.org>`_, and released under the Apache 2.0 License.

It supports Python 3.7, 3.6, 3.5, and 3.4.
2.7 is currently supported but will be dropped from future releases; see :ref:`python2`.
