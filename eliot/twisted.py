"""
APIs for using Eliot from Twisted.
"""

from __future__ import absolute_import, unicode_literals

import os
import sys
from pprint import pformat

from twisted.python import log
from twisted.python.failure import Failure

from ._action import currentAction
from . import addDestination


__all__ = ["AlreadyFinished", "DeferredContext", "redirectLogsForTrial"]



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
        self._finishAdded = False
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

        @raises AlreadyFinished: L{DeferredContext.addActionFinish} has been
            called. This indicates a programmer error.
        """
        if self._finishAdded:
            raise AlreadyFinished()
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

        @raises AlreadyFinished: L{DeferredContext.addActionFinish} has been
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

        @raises AlreadyFinished: L{DeferredContext.addActionFinish} has been
            called. This indicates a programmer error.
        """
        return self.addCallbacks(_passthrough, errback, errbackArgs=args,
                                 errbackKeywords=kw)


    def addBoth(self, callback, *args, **kw):
        """
        Add a single callback as both success and failure callbacks.

        @return: C{self}
        @rtype: L{DeferredContext}

        @raises AlreadyFinished: L{DeferredContext.addActionFinish} has been
            called. This indicates a programmer error.
        """
        return self.addCallbacks(callback, callback, args, kw, args, kw)


    def addActionFinish(self):
        """
        Indicates all callbacks that should run within the action's context have
        been added, and that the action should therefore finish once those
        callbacks have fired.

        @return: The wrapped L{Deferred}.

        @raises AlreadyFinished: L{DeferredContext.addActionFinish} has been
            called previously. This indicates a programmer error.
        """
        if self._finishAdded:
            raise AlreadyFinished()
        self._finishAdded = True
        def done(result):
            if isinstance(result, Failure):
                exception = result.value
            else:
                exception = None
            self._action.finish(exception)
            return result
        self.result.addBoth(done)
        return self.result



def redirectLogsForTrial(sys=sys, log=log):
    """
    When run inside a I{trial} process redirect Eliot log messages to
    Twisted's logging system, otherwise do nothing.

    This allows reading Eliot logs output by running unit tests with
    I{trial} in its normal log location: C{_trial_temp/test.log}.

    This function can usually be safely called in all programs since it will
    have no side-effects if used outside of trial. The only exception is you
    are redirecting Twisted logs to Eliot; you should make sure not call
    this function in that case so as to prevent infinite loops.

    Currently this works by checking if C{sys.argv[0]} is called C{trial};
    the ideal mechanism would require
    https://twistedmatrix.com/trac/ticket/6939 to be fixed, but probably
    there are better solutions even without that -
    https://github.com/hybridcluster/eliot/issues/76 covers those.

    @param sys: An object similar to, and by default identical to, Python's
        L{sys} module.

    @param log: An object similar to, and by default identical to,
        L{twisted.python.log}.

    @return: The destination added to Eliot if any, otherwise L{None}.
    """
    def _logEliotMessage(message):
        log.msg("ELIOT: " + pformat(message))
        if message.get("message_type") == "eliot:traceback":
            log.msg("ELIOT Extracted Traceback:\n" + message["traceback"])

    if os.path.basename(sys.argv[0]) == 'trial':
        addDestination(_logEliotMessage)
        return _logEliotMessage
