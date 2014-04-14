Eliot: Logging as Storytelling
==============================

Eliot provides a structured logging system for Python that generates as a forest
of nested actions. Action start and eventually finish, successfully or not. Log
messages thus tell a story: what happened, and what caused it.

Features:

* Structured, typed messages.
* Action tree, with messages automatically figuring out their action context.
* Excellent support for unit testing your logging code.
* Twisted support.
* JSON output, usable by Logstash/Elasticsearch.

Eliot is released by http://www.hybridcluster.com under the Apache 2.0 License
and maintained by Itamar Turner-Trauring.
