Reading and Filtering Eliot Logs
================================

Eliot includes a command-line tool that makes it easier to read JSON-formatted Eliot messages:

.. code-block:: shell-session

   $ python examples/stdout.py | eliot-prettyprint
   af79ef5c-280c-4b9f-9652-e14deb85d52d@/1
   2015-09-25T19:41:37.850208Z
     another: 1
     value: hello

   0572701c-e791-48e8-9dd2-1fb3bf06826f@/1
   2015-09-25T19:41:38.050767Z
     another: 2
     value: goodbye

The third-party `eliot-tree`_ tool renders JSON-formatted Eliot messages into a tree visualizing the tasks' actions.


Filtering logs
--------------

Eliot logs are structured, and by default stored in one JSON per line.
That means you can filter them in multiple ways:

1. Line-oriented tools like grep.
   You can grep for a particular task's UUIDs, or for a particular message type (e.g. tracebacks).
2. JSON-based filtering tools.
   `jq`_ allows you to filter a stream of JSON messages.
3. `eliot-tree`_ has some filtering and searching support built-in.

For example, here's how you'd extract a particular field with `jq`_:

.. code-block:: shell-session

   $ python examples/stdout.py | jq '.value'
   "hello"
   "goodbye"

.. _eliot-tree: https://github.com/jonathanj/eliottree
.. _jq: https://stedolan.github.io/jq/
