"""
Support for asyncio coroutines.
"""

try:
    from asyncio import Task
except ImportError:
    Task = None  # Python 2
from weakref import WeakKeyDictionary

from ._action import _ExecutionContext


class AsyncioSubContext:
    """
    Per-Task context, allowing different coroutines to have different logging
    context.

    This will be attached to threading.local object, so no need to worry about
    thread-safety.
    """
    def __init__(self):
        self._per_task = WeakKeyDictionary()

    def get_stack(self):
        """
        Get the stack for the current Task, or None if there is no Task.
        """
        try:
            task = Task.current_task()
        except RuntimeError:
            # No loop for this thread:
            task = None
        if task is None:
            return None
        if task not in self._per_task:
            self._per_task[task] = []
        return self._per_task[task]


class AsyncioExecutionContext(_ExecutionContext):
    """ExecutionContext that supports asyncio sub-contexts."""

    def __init__(self):
        _ExecutionContext.__init__(self)
        self.get_sub_context = AsyncioSubContext().get_stack


def use_asyncio_context():
    """
    Use a logging context that is tied to the current asyncio coroutine.

    Call this first thing, before doing any other logging.

    Does not currently support event loops other than asyncio.
    """
    # XXX deprecationwarning
