.. _asyncio_coroutine:

Asyncio Coroutine Support
=========================

If you're using ``asyncio`` coroutines in Python 3.5 or later (``async def yourcoro()`` and ``await yourcoro()``) together with Eliot, you need to run the following before doing any logging:

.. code-block:: python

   import eliot
   eliot.use_asyncio_context()


Why you need to do this
-----------------------
By default Eliot provides a different "context" for each thread.
That is how ``with start_action(action_type='my_action'):`` works: it records the current action on this context.

When using coroutines you end up with the same context being used with different coroutines, since they share the same thread.
Calling ``eliot.use_asyncio_context()`` makes sure each coroutine gets its own context, so ``with start_action()`` in one coroutine doesn't interfere with another.

However, Eliot will do the right thing for nested coroutines.
Specifically, coroutines called via ``await a_coroutine()`` will inherit the logging context from the calling coroutine.


Limitations
-----------

* I haven't tested the Python 3.4 ``yield from`` variation.
* This doesn't support other event loops (Curio, Trio, Tornado, etc.).
  If you want these supported please file an issue: https://github.com/itamarst/eliot/issues/new
  There is talk of adding the concept of a coroutine context to Python 3.7 or perhaps 3.8, in which case it will be easier to automatically support all frameworks.
