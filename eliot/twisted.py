"""
APIs for using Eliot from Twisted.
"""

from __future__ import absolute_import, unicode_literals

from twisted.python.failure import Failure

from ._action import currentAction

__all__ = ["AlreadyFinished", "DeferredContext"]



def _passthrough(result):
    return result



class AlreadyFinished(Exception):
    """
    L{DeferredContext.addCallbacks} or similar method was called after
    L{DeferredContext.addActionFinish}.

    This indicates a programming bug, e.g. forgetting to unwrap the
    underlying L{Deferred} when passing on to some other piece of code that
    doesn't care about the action context.
    """



class DeferredContext(object):
    """
    A L{Deferred} equivalent of L{eliot.Action.context} and
    L{eliot.action.finish}.

    Makes a L{Deferred}'s callbacks run in a L{eliot.Action}'s context, and
    allows indicating which callbacks to wait for before the action is
    finished.

    The action to use will be taken from the call context.

    @ivar result: The wrapped L{Deferred}.
    """
    def __init__(self, deferred):
        """
        @param deferred: L{twisted.internet.defer.Deferred} to wrap.
        """
        self.result = deferred
        self._action = currentAction()
        if self._action is None:
            raise RuntimeError(
                "DeferredContext() should only be created in the context of an "
                "eliot.Action.")


    def addCallbacks(self, callback, errback,
                     callbackArgs=None, callbackKeywords=None,
                     errbackArgs=None, errbackKeywords=None):
        """
        Add a pair of callbacks that will be run in the context of an eliot
        action.

        @return: C{self}
        @rtype: L{DeferredContext}

        @raises AlreadyFinished: L{DeferredContext.finishAfter} has been
            called. This indicates a programmer error.
        """
        def callbackWithContext(*args, **kwargs):
            return self._action.run(callback, *args, **kwargs)
        def errbackWithContext(*args, **kwargs):
            return self._action.run(errback, *args, **kwargs)
        self.result.addCallbacks(callbackWithContext, errbackWithContext,
                                 callbackArgs, callbackKeywords, errbackArgs,
                                 errbackKeywords)
        return self


    def addCallback(self, callback, *args, **kw):
        """
        Add a success callback that will be run in the context of an eliot
        action.

        @return: C{self}
        @rtype: L{DeferredContext}

        @raises AlreadyFinished: L{DeferredContext.finishAfter} has been
            called. This indicates a programmer error.
        """
        return self.addCallbacks(callback, _passthrough, callbackArgs=args,
                                 callbackKeywords=kw)


    def addErrback(self, errback, *args, **kw):
        """
        Add a failure callback that will be run in the context of an eliot
        action.

        @return: C{self}
        @rtype: L{DeferredContext}

        @raises AlreadyFinished: L{DeferredContext.finishAfter} has been
            called. This indicates a programmer error.
        """
        return self.addCallbacks(_passthrough, errback, errbackArgs=args,
                                 errbackKeywords=kw)


    def addBoth(self, callback, *args, **kw):
        """
        Add a single callback as both success and failure callbacks.

        @return: C{self}
        @rtype: L{DeferredContext}

        @raises AlreadyFinished: L{DeferredContext.finishAfter} has been
            called. This indicates a programmer error.
        """
        return self.addCallbacks(callback, callback, args, kw, args, kw)


    def addActionFinish(self):
        """
        Indicates all callbacks that should run within the action's context have
        been added, and that the action should therefore finish once those
        callbacks have fired.
        """
        def done(result):
            if isinstance(result, Failure):
                exception = result.value
            else:
                exception = None
            self._action.finish(exception)
            return result
        self.result.addBoth(done)
