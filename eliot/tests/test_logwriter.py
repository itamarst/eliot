"""
Tests for L{eliot.logwriter}.
"""

from __future__ import unicode_literals

import time
import threading
# Make sure to use StringIO that only accepts unicode:
from io import BytesIO, StringIO
from unittest import skipIf
import json as pyjson
from warnings import catch_warnings, simplefilter

from six import PY2

try:
    from zope.interface.verify import verifyClass
    from twisted.internet import reactor
    from twisted.trial.unittest import TestCase
    from twisted.application.service import IService
    from twisted.python import threadable
except ImportError:
    # Make tests not run at all.
    TestCase = object
else:
    # Make sure we always import this if Twisted is available, so broken
    # logwriter.py causes a failure:
    from ..logwriter import ThreadedFileWriter, ThreadedWriter

from .. import Logger, removeDestination, FileDestination


class BlockingFile(object):
    """
    A file-like whose writes can be blocked.

    Also, allow calling C{getvalue} after C{close}, unlike L{BytesIO}.
    """
    def __init__(self):
        self.file = BytesIO()
        self.lock = threading.Lock()
        self.data = b""


    def block(self):
        """
        Prevent writes until L{unblock} is called.
        """
        self.lock.acquire()


    def unblock(self):
        """
        Allow writes if L{block} was previous called.
        """
        self.lock.release()


    def getvalue(self):
        """
        Get written bytes.

        @return: Written bytes.
        """
        return self.data


    def write(self, data):
        with self.lock:
            self.file.write(data)


    def flush(self):
        self.data = self.file.getvalue()


    def close(self):
        self.file.close()



class ThreadedWriterTests(TestCase):
    """
    Tests for L{ThreadedWriter}.

    Many of these tests involve interactions across threads, so they
    arbitrarily wait for up to 5 seconds to reduce chances of slow thread
    switching causing the test to fail.
    """
    def test_interface(self):
        """
        L{ThreadedWriter} provides L{IService}.
        """
        verifyClass(IService, ThreadedWriter)


    def test_name(self):
        """
        L{ThreadedWriter} has a name.
        """
        self.assertEqual(ThreadedWriter.name, u"Eliot Log Writer")


    def test_startServiceRunning(self):
        """
        L{ThreadedWriter.startService} starts the service as required by the
        L{IService} interface.
        """
        writer = ThreadedWriter(FileDestination(file=BytesIO()), reactor)
        self.assertFalse(writer.running)
        writer.startService()
        self.addCleanup(writer.stopService)
        self.assertTrue(writer.running)


    def test_stopServiceRunning(self):
        """
        L{ThreadedWriter.stopService} stops the service as required by the
        L{IService} interface.
        """
        writer = ThreadedWriter(FileDestination(file=BytesIO()), reactor)
        writer.startService()
        d = writer.stopService()
        d.addCallback(lambda _: self.assertFalse(writer.running))
        return d


    def test_startServiceStartsThread(self):
        """
        L{ThreadedWriter.startService} starts up a thread running
        L{ThreadedWriter._writer}.
        """
        previousThreads = threading.enumerate()
        result = []
        event = threading.Event()
        def _writer():
            current = threading.currentThread()
            if current not in previousThreads:
                result.append(current)
            event.set()
        writer = ThreadedWriter(FileDestination(file=BytesIO()), reactor)
        writer._writer = _writer
        writer.startService()
        event.wait()
        self.assertTrue(result)
        # Make sure thread is dead so it doesn't die half way through another
        # test:
        result[0].join(5)

    def test_stopServiceStopsThread(self):
        """
        L{ThreadedWriter.stopService} stops the writer thread.
        """
        previousThreads = set(threading.enumerate())
        writer = ThreadedWriter(FileDestination(file=BytesIO()), reactor)
        writer.startService()
        start = time.time()
        while set(threading.enumerate()) == previousThreads and (
                time.time() - start < 5):
            time.sleep(0.0001)
        # If not true the next assertion might pass by mistake:
        self.assertNotEqual(set(threading.enumerate()), previousThreads)
        writer.stopService()
        while set(threading.enumerate()) != previousThreads and (
                time.time() - start < 5):
            time.sleep(0.0001)
        self.assertEqual(set(threading.enumerate()), previousThreads)


    def test_stopServiceFinishesWriting(self):
        """
        L{ThreadedWriter.stopService} stops the writer thread, but only after
        all queued writes are written out.
        """
        f = BlockingFile()
        writer = ThreadedWriter(FileDestination(file=f), reactor)
        f.block()
        writer.startService()
        for i in range(100):
            writer({u"write": 123})
        threads = threading.enumerate()
        writer.stopService()
        # Make sure writes didn't happen before the stopService, thus making the
        # test pointless:
        self.assertEqual(f.getvalue(), b"")
        f.unblock()
        start = time.time()
        while threading.enumerate() == threads and time.time() - start < 5:
            time.sleep(0.0001)
        self.assertEqual(f.getvalue(), b'{"write": 123}\n' * 100)


    def test_stopServiceResult(self):
        """
        L{ThreadedWriter.stopService} returns a L{Deferred} that fires only
        after the thread has shut down.
        """
        f = BlockingFile()
        writer = ThreadedWriter(FileDestination(file=f), reactor)
        f.block()
        writer.startService()

        writer({"hello": 123})
        threads = threading.enumerate()
        d = writer.stopService()
        f.unblock()

        def done(_):
            self.assertEqual(f.getvalue(), b'{"hello": 123}\n')
            self.assertNotEqual(threading.enumerate(), threads)
        d.addCallback(done)
        return d


    def test_noChangeToIOThread(self):
        """
        Running a L{ThreadedWriter} doesn't modify the Twisted registered IO
        thread.
        """
        writer = ThreadedWriter(FileDestination(file=BytesIO()), reactor)
        writer.startService()
        d = writer.stopService()
        # Either the current thread (the one running the tests) is the the I/O
        # thread or the I/O thread was never set. Either may happen depending on
        # how and whether the reactor has been started by the unittesting
        # framework.
        d.addCallback(lambda _: self.assertIn(
            threadable.ioThread, (None, threading.currentThread().ident)))
        return d


    def test_startServiceRegistersDestination(self):
        """
        L{ThreadedWriter.startService} registers itself as an Eliot log
        destination.
        """
        f = BlockingFile()
        writer = ThreadedWriter(FileDestination(file=f), reactor)
        writer.startService()
        Logger().write({"x": "abc"})
        d = writer.stopService()
        d.addCallback(lambda _: self.assertIn(b"abc", f.getvalue()))
        return d


    def test_stopServiceUnregistersDestination(self):
        """
        L{ThreadedWriter.stopService} unregisters itself as an Eliot log
        destination.
        """
        writer = ThreadedWriter(FileDestination(file=BytesIO()), reactor)
        writer.startService()
        d = writer.stopService()
        d.addCallback(lambda _: removeDestination(writer))
        return self.assertFailure(d, ValueError)


    def test_call(self):
        """
        The message passed to L{ThreadedWriter.__call__} is passed to the
        underlying destination in the writer thread.
        """
        result = []

        def destination(message):
            result.append((message, threading.currentThread().ident))

        writer = ThreadedWriter(destination, reactor)
        writer.startService()
        thread_ident = writer._thread.ident
        msg = {"key": 123}
        writer(msg)
        d = writer.stopService()
        d.addCallback(
            lambda _: self.assertEqual(result, [(msg, thread_ident)]))
        return d


class ThreadedFileWriterTests(TestCase):
    """
    Tests for ``ThreadedFileWriter``.
    """
    def test_deprecation_warning(self):
        """
        Instantiating ``ThreadedFileWriter`` gives a ``DeprecationWarning``.
        """
        with catch_warnings(record=True) as warnings:
            ThreadedFileWriter(BytesIO(), reactor)
            simplefilter("always")  # Catch all warnings
            self.assertEqual(warnings[-1].category, DeprecationWarning)

    def test_write(self):
        """
        Messages passed to L{ThreadedFileWriter.__call__} are then written by
        the writer thread with a newline added.
        """
        f = BytesIO()
        writer = ThreadedFileWriter(f, reactor)
        writer.startService()
        self.addCleanup(writer.stopService)

        writer({"hello": 123})
        start = time.time()
        while not f.getvalue() and time.time() - start < 5:
            time.sleep(0.0001)
        self.assertEqual(f.getvalue(), b'{"hello": 123}\n')

    @skipIf(PY2, "Python 2 files always accept bytes")
    def test_write_unicode(self):
        """
        Messages passed to L{ThreadedFileWriter.__call__} are then written by
        the writer thread with a newline added to files that accept
        unicode.
        """
        f = StringIO()
        writer = ThreadedFileWriter(f, reactor)
        writer.startService()
        self.addCleanup(writer.stopService)

        original = {"hello\u1234": 123}
        writer(original)
        start = time.time()
        while not f.getvalue() and time.time() - start < 5:
            time.sleep(0.0001)
        self.assertEqual(f.getvalue(), pyjson.dumps(original) + "\n")

    def test_stopServiceClosesFile(self):
        """
        L{ThreadedWriter.stopService} closes the file.
        """
        f = BytesIO()
        writer = ThreadedFileWriter(f, reactor)
        writer.startService()
        d = writer.stopService()

        def done(_):
            self.assertTrue(f.closed)
        d.addCallback(done)
        return d
