"""
A log destination for use by Twisted applications.

Runs in a thread, so that we don't do blocking I/O in the event loop thread.
"""

import threading
from queue import SimpleQueue

from twisted.application.service import Service
from twisted.internet.threads import deferToThreadPool

from . import addDestination, removeDestination

_STOP = object()


class ThreadedWriter(Service):
    """
    An non-blocking Eliot log destination that wraps a blocking
    destination, writing log messages to the latter in a managed thread.

    @ivar _thread: C{None}, or a L{threading.Thread} running the private
        reactor.
    """

    name = "Eliot Log Writer"

    def __init__(self, destination, reactor):
        """
        @param destination: The underlying destination for log files. This will
            be called from a non-reactor thread.

        @param reactor: The main reactor.
        """
        self._destination = destination
        self._queue = SimpleQueue()
        self._mainReactor = reactor
        self._thread = None

    def startService(self):
        """
        Start the writer thread.
        """
        Service.startService(self)
        self._thread = threading.Thread(target=self._reader)
        self._thread.start()
        addDestination(self)

    def stopService(self):
        """
        Stop the writer thread, wait for it to finish.
        """
        Service.stopService(self)
        removeDestination(self)
        self._queue.put(_STOP)
        return deferToThreadPool(
            self._mainReactor, self._mainReactor.getThreadPool(), self._thread.join
        )

    def __call__(self, data):
        """
        Add the data to the queue, to be serialized to JSON and written by the
        writer thread with a newline added.

        @param data: C{bytes} to write to disk.
        """
        self._queue.put(data)

    def _reader(self):
        """
        Runs in a thread, reads messages from a queue and writes them to
        the wrapped observer.
        """
        while True:
            msg = self._queue.get()
            if msg is _STOP:
                return
            try:
                self._destination(msg)
            except Exception:
                # Lower-level destination blew up, nothing we can do, so
                # just drop on the floor.
                pass
