"""
A log destination for use by Twisted applications.

Runs in a thread, so that we don't do blocking I/O in the event loop thread.
"""

from __future__ import unicode_literals, absolute_import

import threading
import select

from twisted.application.service import Service
from twisted.internet.threads import deferToThreadPool
if getattr(select, "poll", None):
    from twisted.internet.pollreactor import PollReactor as Reactor
else:
    from twisted.internet.selectreactor import SelectReactor as Reactor

from . import addDestination, removeDestination
from ._output import _FileDestination


class ThreadedFileWriter(Service):
    """
    An Eliot log destination that writes log messages as lines to a file, using
    a managed thread.

    Unfortunately Python's Queue is not reentrant
    (http://bugs.python.org/issue14976) and neither is RLock
    (http://bugs.python.org/issue13697). In order to queue items in a thread we
    therefore rely on the self-pipe trick, and the easiest way to do that is by
    running another reactor in the thread.

    @ivar _reactor: A private reactor running in a thread which will do the log
        writes.

    @ivar _thread: C{None}, or a L{threading.Thread} running the private
        reactor.
    """
    name = u"Eliot Log Writer"


    def __init__(self, logFile, reactor):
        """
        @param logFile: A C{file}-like object that is at the end of its existing
           contents (e.g. opened with append mode) and accepts bytes.
        @type logFile: C{file}, or any file-like object with C{write}, C{flush}
            and C{close} methods e.g. a L{twisted.python.logfile.LogFile} if you
            want log rotation.

        @param reactor: The main reactor.
        """
        self._logFile = logFile
        self._destination = _FileDestination(file=logFile)
        self._reactor = Reactor()
        # Ick. See https://twistedmatrix.com/trac/ticket/6982 for real solution.
        self._reactor._registerAsIOThread = False
        self._mainReactor = reactor
        self._thread = None


    def startService(self):
        """
        Start the writer thread.
        """
        Service.startService(self)
        self._thread = threading.Thread(target=self._writer)
        self._thread.start()
        addDestination(self)


    def stopService(self):
        """
        Stop the writer thread, wait for it to finish.
        """
        Service.stopService(self)
        removeDestination(self)
        self._reactor.callFromThread(self._reactor.stop)
        return deferToThreadPool(
            self._mainReactor, self._mainReactor.getThreadPool(),
            self._thread.join)


    def __call__(self, data):
        """
        Add the data to the queue, to be serialized to JSON and written by the
        writer thread with a newline added.

        @param data: C{bytes} to write to disk.
        """
        self._reactor.callFromThread(self._destination, data)


    def _writer(self):
        """
        The function run by the writer thread.
        """
        self._reactor.run(installSignalHandlers=False)
        self._logFile.close()
