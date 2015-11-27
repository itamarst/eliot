Using Logstash and ElasticSearch to Process Eliot Logs
======================================================

`ElasticSearch`_ is a search and analytics engine which can be used to store Eliot logging output.
The logs can then be browsed by humans using the `Kibana`_ web UI, or on the command-line using the `logstash-cli`_ tool.
Automated systems can access the logs using the ElasticSearch query API.
`Logstash`_ is a log processing tool that can be used to load Eliot log files into ElasticSearch.
The combination of ElasticSearch, Logstash, and Kibana is sometimes referred to as ELK.

.. _logstash-cli: https://github.com/jedi4ever/logstash-cli
.. _Logstash: http://logstash.net/
.. _ElasticSearch: http://elasticsearch.org
.. _Kibana: http://www.elasticsearch.org/overview/kibana/


Example Logstash Configuration
------------------------------

Assuming each Eliot message is written out as a JSON message on its own line (which is the case for ``eliot.to_file()`` and ``eliot.logwriter.ThreadedFileWriter``), the following Logstash configuration will load these log messages into an in-process ElasticSearch database:

:download:`logstash_standalone.conf`

.. literalinclude:: logstash_standalone.conf

We can then pipe JSON messages from Eliot into ElasticSearch using Logstash:

.. code-block:: console

    $ python examples/stdout.py | logstash web -- agent --config logstash_standalone.conf

You can then use the Kibana UI to search and browse the logs by visiting http://localhost:9292/.
