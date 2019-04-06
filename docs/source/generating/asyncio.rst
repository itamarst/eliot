.. _asyncio_coroutine:

Asyncio/Trio Coroutine Support
==============================

As of Eliot 1.8, ``asyncio`` and ``trio`` coroutines have appropriate context propogation for Eliot, automatically.

On Python 3.7 or later, no particular care is needed.
For Python 3.5 and 3.6 you will need to import either ``eliot`` (or the backport package ``aiocontextvars``) before you create your first event loop.
