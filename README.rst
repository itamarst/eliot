Eliot: Logging for Complex & Distributed Systems
================================================

.. image:: https://coveralls.io/repos/ClusterHQ/eliot/badge.png?branch=master
           :target: https://coveralls.io/r/ClusterHQ/eliot
           :alt: Coveralls test coverage information

.. image:: https://travis-ci.org/ClusterHQ/eliot.png?branch=master
           :target: http://travis-ci.org/ClusterHQ/eliot
           :alt: Build Status

Eliot is a Python logging system designed not only for simple applications but for complex applications as well, including distributed systems.
Eliot supports simple structured messages but can also record a causal chain of actions happening within and across process boundaries: a logical trace of the system's operation.

Structured, action-oriented logging is a great help when debugging problems.
For example, here are the combined logs of a request originating from a client process being sent to a server.
Notice how easy it is to figure out the cause of the problem, even though it's opaque to the client::

    process='client' task_uuid='40be6df2' task_level=[1] action_type='main'
        action_status='started'

    process='client' task_uuid='40be6df2' task_level=[2, 1] action_type='http_request'
        action_status='started' x=5 y=0

    process='server' task_uuid='40be6df2' task_level=[2, 2, 1] action_type='eliot:remote_task'
        action_status='started'

    process='server' task_uuid='40be6df2' task_level=[2, 2, 2, 1] action_type='divide'
        action_status='started' x=5 y=0

    process='server' task_uuid='40be6df2' task_level=[2, 2, 2, 2] action_type='divide'
        action_status='failed' exception='exceptions.ZeroDivisionError' reason='integer division or modulo by zero'

    process='server' task_uuid='40be6df2' task_level=[2, 2, 3] action_type='eliot:remote_task'
        action_status='failed' exception='exceptions.ZeroDivisionError' reason='integer division or modulo by zero'

    process='client' task_uuid='40be6df2' task_level=[2, 3] action_type='http_request'
       action_status='failed' exception='requests.exception.HTTPError' reason='500 Server Error: INTERNAL SERVER ERROR'

    process='client' task_uuid='40be6df2' task_level=[3] action_type='main'
       action_status='failed' exception='requests.exception.HTTPError' reason='500 Server Error: INTERNAL SERVER ERROR'


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
