"""
Support for asyncio coroutines.


"""



def use_asyncio_context():
    """
    Use a logging context that is tied to the current asyncio coroutine.

    Call this first thing, before doing any other logging.

    Does not currently support event loops other than asyncio.
    """
    # XXX deprecationwarning
