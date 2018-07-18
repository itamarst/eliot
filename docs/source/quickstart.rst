Quickstart
==========

Let's see how easy it is to use Eliot.


Installing Eliot
----------------

To install Eliot and the other tools we'll use in this example, run the following in your shell:

.. code-block:: shell-session

   $ pip install eliot eliot-tree requests

This will install:

1. Eliot itself.
2. `eliot-tree <https://github.com/jonathanj/eliottree>`_, a tool that lets you visualize Eliot logs easily.
3. ``requests``, a HTTP client library we'll use in the example code below.
   You don't need it for real Eliot usage, though.


Our example program
-------------------

We're going to add logging code to the following script, which checks if a list of links are valid URLs:

.. code-block:: python

   import requests

   def check_links(urls):
       for url in urls:
           try:
               response = requests.get(url)
               response.raise_for_status()
           except Exception as e:
               raise ValueError(str(e))

   try:
       check_links(["http://eliot.readthedocs.io", "http://nosuchurl"])
   except ValueError:
       print("Not all links were valid.")


Adding Eliot logging
--------------------

To add logging to this program, we do two things:

1. Tell Eliot to log messages to file called "linkcheck.log" by using ``eliot.to_file()``.
2. Create two actions using ``eliot.start_action()``.
   Actions succeed when the ``eliot.start_action()`` context manager finishes successfully, and fail when an exception is raised.

.. literalinclude:: ../../examples/linkcheck.py
   :emphasize-lines: 2,3,7,10


Running the code
----------------

Let's run the code:

.. code-block:: shell-session

   $ python linkcheck.py
   Not all the links were valid.

We can see the resulting log file is composed of JSON messages, one per line:

.. code-block:: shell-session

   $ cat linkcheck.log
   {"action_status": "started", "task_uuid": "b1cb58cf-2c2f-45c0-92b2-838ac00b20cc", "task_level": [1], "timestamp": 1509136967.2066844, "action_type": "check_links", "urls": ["http://eliot.readthedocs.io", "http://nosuchurl"]}
   ...

So far these logs seem similar to the output of regular logging systems: individual isolated messages.
But unlike those logging systems, Eliot produces logs that can be reconstructed into a tree, for example using the ``eliot-tree`` utility:

.. code-block:: shell-session
   :emphasize-lines: 3,8,13,16-19,21-23

   $ eliot-tree linkcheck.log
   b1cb58cf-2c2f-45c0-92b2-838ac00b20cc
   └── check_links/1 ⇒ started
       ├── timestamp: 2017-10-27 20:42:47.206684
       ├── urls: 
       │   ├── 0: http://eliot.readthedocs.io
       │   └── 1: http://nosuchurl
       ├── download/2/1 ⇒ started
       │   ├── timestamp: 2017-10-27 20:42:47.206933
       │   ├── url: http://eliot.readthedocs.io
       │   └── download/2/2 ⇒ succeeded
       │       └── timestamp: 2017-10-27 20:42:47.439203
       ├── download/3/1 ⇒ started
       │   ├── timestamp: 2017-10-27 20:42:47.439412
       │   ├── url: http://nosuchurl
       │   └── download/3/2 ⇒ failed
       │       ├── errno: None
       │       ├── exception: requests.exceptions.ConnectionError
       │       ├── reason: HTTPConnectionPool(host='nosuchurl', port=80): Max retries exceeded with url: / (Caused by NewConnec…
       │       └── timestamp: 2017-10-27 20:42:47.457133
       └── check_links/4 ⇒ failed
           ├── exception: builtins.ValueError
           ├── reason: HTTPConnectionPool(host='nosuchurl', port=80): Max retries exceeded with url: / (Caused by NewConnec…
           └── timestamp: 2017-10-27 20:42:47.457332

Notice how:

1. Eliot tells you which actions succeeded and which failed.
2. Failed actions record their exceptions.
3. You can see just from the logs that the ``check_links`` action caused the ``download`` action.

Next steps
----------

You can learn more by reading the rest of the documentation, including:

* The :doc:`motivation behind Eliot <introduction>`.
* How to generate :doc:`actions <generating/actions>`, :doc:`standalone messages <generating/messages>`, and :doc:`handle errors <generating/errors>`.
* How to integrate or migrate your :doc:`existing stdlib logging messages <generating/migrating>`.
* How to output logs :doc:`to a file or elsewhere <outputting/output>`.
* Using :doc:`asyncio coroutines <generating/asyncio>`, :doc:`threads and processes <generating/threads>`, or :doc:`Twisted <generating/twisted>`.
