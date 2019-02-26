"""
Support for maintaining an action context across generator suspension.
"""

from __future__ import unicode_literals, absolute_import

from sys import exc_info
from functools import wraps
from contextlib import contextmanager
from weakref import WeakKeyDictionary

from ._action import _context

from . import (
    Message,
)

class _GeneratorContext(object):
    def __init__(self, execution_context):
        self._execution_context = execution_context
        self._contexts = WeakKeyDictionary()
        self._current_generator = None

    def init_stack(self, generator):
        stack = list(self._execution_context._get_stack())
        self._contexts[generator] = stack

    def get_stack(self):
        if self._current_generator is None:
            # If there is no currently active generator then we have no
            # special stack to supply.  Let the execution context figure out a
            # different answer on its own.
            return None
        # Otherwise, give back the action context stack we've been tracking
        # for the currently active generator.  It must have been previously
        # initialized (it's too late to do it now)!
        return self._contexts[self._current_generator]

    @contextmanager
    def context(self, generator):
        previous_generator = self._current_generator
        try:
            self._current_generator = generator
            yield
        finally:
            self._current_generator = previous_generator


_the_generator_context = _GeneratorContext(_context)


def use_generator_context():
    """
    Make L{eliot_friendly_generator_function} work correctly.
    """
    _context.get_sub_context = _the_generator_context.get_stack


def _installed():
    return _context.get_sub_context == _the_generator_context.get_stack


class GeneratorSupportNotEnabled(Exception):
    """
    An attempt was made to use a decorated generator without first turning on
    the generator context manager.
    """


def eliot_friendly_generator_function(original):
    """
    Decorate a generator function so that the Eliot action context is
    preserved across ``yield`` expressions.
    """
    @wraps(original)
    def wrapper(*a, **kw):
        # This isn't going to work if you don't have the generator context
        # manager installed.
        if not _installed():
            raise GeneratorSupportNotEnabled()

        # Keep track of whether the next value to deliver to the generator is
        # a non-exception or an exception.
        ok = True

        # Keep track of the next value to deliver to the generator.
        value_in = None

        # Create the generator with a call to the generator function.  This
        # happens with whatever Eliot action context happens to be active,
        # which is fine and correct and also irrelevant because no code in the
        # generator function can run until we call send or throw on it.
        gen = original(*a, **kw)

        # Initialize the per-generator Eliot action context stack to the
        # current action stack.  This might be the main stack or, if another
        # decorated generator is running, it might be the stack for that
        # generator.  Not our business.
        _the_generator_context.init_stack(gen)
        while True:
            try:
                # Whichever way we invoke the generator, we will do it
                # with the Eliot action context stack we've saved for it.
                # Then the context manager will re-save it and restore the
                # "outside" stack for us.
                #
                # Regarding the support of Twisted's inlineCallbacks-like
                # functionality (see eliot.twisted.inline_callbacks):
                #
                # The invocation may raise the inlineCallbacks internal
                # control flow exception _DefGen_Return.  It is not wrong to
                # just let that propagate upwards here but inlineCallbacks
                # does think it is wrong.  The behavior triggers a
                # DeprecationWarning to try to get us to fix our code.  We
                # could explicitly handle and re-raise the _DefGen_Return but
                # only at the expense of depending on a private Twisted API.
                # For now, I'm opting to try to encourage Twisted to fix the
                # situation (or at least not worsen it):
                # https://twistedmatrix.com/trac/ticket/9590
                #
                # Alternatively, _DefGen_Return is only required on Python 2.
                # When Python 2 support is dropped, this concern can be
                # eliminated by always using `return value` instead of
                # `returnValue(value)` (and adding the necessary logic to the
                # StopIteration handler below).
                with _the_generator_context.context(gen):
                    if ok:
                        value_out = gen.send(value_in)
                    else:
                        value_out = gen.throw(*value_in)
                    # We have obtained a value from the generator.  In
                    # giving it to us, it has given up control.  Note this
                    # fact here.  Importantly, this is within the
                    # generator's action context so that we get a good
                    # indication of where the yield occurred.
                    #
                    # This might be too noisy, consider dropping it or
                    # making it optional.
                    Message.log(message_type=u"yielded")
            except StopIteration:
                # When the generator raises this, it is signaling
                # completion.  Leave the loop.
                break
            else:
                try:
                    # Pass the generator's result along to whoever is
                    # driving.  Capture the result as the next value to
                    # send inward.
                    value_in = yield value_out
                except:
                    # Or capture the exception if that's the flavor of the
                    # next value.  This could possibly include GeneratorExit
                    # which turns out to be just fine because throwing it into
                    # the inner generator effectively propagates the close
                    # (and with the right context!) just as you would want.
                    # True, the GeneratorExit does get re-throwing out of the
                    # gen.throw call and hits _the_generator_context's
                    # contextmanager.  But @contextmanager extremely
                    # conveniently eats it for us!  Thanks, @contextmanager!
                    ok = False
                    value_in = exc_info()
                else:
                    ok = True

    return wrapper
