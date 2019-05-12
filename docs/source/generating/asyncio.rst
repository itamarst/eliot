.. _asyncio_coroutine:

Asyncio/Trio Coroutine Support
==============================

As of Eliot 1.8, ``asyncio`` and ``trio`` coroutines have appropriate context propogation for Eliot, automatically.

Asyncio
--------

On Python 3.7 or later, no particular care is needed.
For Python 3.5 and 3.6 you will need to import either ``eliot`` (or the backport package ``aiocontextvars``) before you create your first event loop.

Here's an example using ``aiohttp``:

.. literalinclude:: ../../../examples/asyncio_linkcheck.py

And the resulting logs:

.. code-block:: shell-session

  $ eliot-tree linkcheck.log
  0a9a5e1b-330c-4251-b7db-fd3161403443
  └── check_links/1 ⇒ started 2019-04-06 19:49:16 ⧖ 0.535s
      ├── urls: 
      │   ├── 0: http://eliot.readthedocs.io
      │   └── 1: http://nosuchurl
      ├── download/2/1 ⇒ started 2019-04-06 19:49:16 ⧖ 0.527s
      │   ├── url: http://eliot.readthedocs.io
      │   └── download/2/2 ⇒ succeeded 2019-04-06 19:49:16
      ├── download/3/1 ⇒ started 2019-04-06 19:49:16 ⧖ 0.007s
      │   ├── url: http://nosuchurl
      │   └── download/3/2 ⇒ failed 2019-04-06 19:49:16
      │       ├── errno: -2
      │       ├── exception: aiohttp.client_exceptions.ClientConnectorError
      │       └── reason: Cannot connect to host nosuchurl:80 ssl:None [Name or service not known]                                                                                           
      └── check_links/4 ⇒ failed 2019-04-06 19:49:16
          ├── exception: builtins.ValueError
          └── reason: Cannot connect to host nosuchurl:80 ssl:None [Name or service not known]


Trio
----

Here's an example of using Trio—we put the action outside the nursery so that it finishes only when the nursery shuts down.

.. literalinclude:: ../../../examples/trio_say.py

And the resulting logs:

.. code-block:: shell-session

  $ eliot-tree trio.log
  93a4de27-8c95-498b-a188-f0e91482ad10
  └── main/1 ⇒ started 2019-04-10 21:07:20 ⧖ 2.003s                                            
      ├── say/2/1 ⇒ started 2019-04-10 21:07:20 ⧖ 2.002s                                       
      │   ├── message: world
      │   └── say/2/2 ⇒ succeeded 2019-04-10 21:07:22                                          
      ├── say/3/1 ⇒ started 2019-04-10 21:07:20 ⧖ 1.001s                                       
      │   ├── message: hello
      │   └── say/3/2 ⇒ succeeded 2019-04-10 21:07:21                                          
      └── main/4 ⇒ succeeded 2019-04-10 21:07:22

If you put the ``start_action`` *inside* the nursery context manager:

1. The two ``say`` calls will be scheduled, but not started.
2. The parent action will end.
3. Only then will the child actions be created.

The result is somewhat confusing output.
Trying to improve this situation is covered in `issue #401 <https://github.com/itamarst/eliot/issues/401>`_.
