Reading Eliot Logs
==================

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
Unlike ``eliot-prettyprint`` it may not be able to format all messages if some of a task's messages are missing.

.. _eliot-tree: https://warehouse.python.org/project/eliot-tree/
