"""
Support for maintaining an action context across generator suspension.
"""


from sys import exc_info
from functools import wraps
from contextlib import contextmanager
from contextvars import copy_context
from weakref import WeakKeyDictionary

from . import log_message


class _GeneratorContext(object):
    """Generator sub-context for C{_ExecutionContext}."""

    def __init__(self, execution_context):
        self._execution_context = execution_context
        self._contexts = WeakKeyDictionary()
        self._current_generator = None

    def init_stack(self, generator):
        """Create a new stack for the given generator."""
        self._contexts[generator] = copy_context()

    @contextmanager
    def in_generator(self, generator):
        """Context manager: set the given generator as the current generator."""
        previous_generator = self._current_generator
        try:
            self._current_generator = generator
            yield
        finally:
            self._current_generator = previous_generator


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

        # Initialize the per-generator context to a copy of the current context.
        context = copy_context()
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
                def go():
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
                    # This is noisy, enable only for debugging:
                    if wrapper.debug:
                        log_message(message_type="yielded")
                    return value_out

                value_out = context.run(go)
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

    wrapper.debug = False
    return wrapper
