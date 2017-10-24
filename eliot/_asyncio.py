"""
Support for asyncio coroutines.
"""

from asyncio import Task
from weakref import WeakKeyDictionary


class AsyncioContext:
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
