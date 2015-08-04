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
    from ..logwriter import ThreadedFileWriter

from .. import Logger, removeDestination


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
        self.data = self.file.getvalue()


    def close(self):
        self.file.close()



class ThreadedFileWriterTests(TestCase):
    """
    Tests for L{ThreadedFileWriter}.

    Many of these tests involve interactions across threads, so they
    arbitrarily wait for up to 5 seconds to reduce chances of slow thread
    switching causing the test to fail.
    """
    def test_interface(self):
        """
        L{ThreadedFileWriter} provides L{IService}.
        """
        verifyClass(IService, ThreadedFileWriter)


    def test_name(self):
        """
        L{ThreadedFileWriter} has a name.
        """
        self.assertEqual(ThreadedFileWriter.name, u"Eliot Log Writer")


    def test_startServiceRunning(self):
        """
        L{ThreadedFileWriter.startService} starts the service as required by the
        L{IService} interface.
        """
        writer = ThreadedFileWriter(BytesIO(), reactor)
        self.assertFalse(writer.running)
        writer.startService()
        self.addCleanup(writer.stopService)
        self.assertTrue(writer.running)


    def test_stopServiceRunning(self):
        """
        L{ThreadedFileWriter.stopService} stops the service as required by the
        L{IService} interface.
        """
        writer = ThreadedFileWriter(BytesIO(), reactor)
        writer.startService()
        d = writer.stopService()
        d.addCallback(lambda _: self.assertFalse(writer.running))
        return d


    def test_startServiceStartsThread(self):
        """
        L{ThreadedFileWriter.startService} starts up a thread running
        L{ThreadedFileWriter._writer}.
        """
        previousThreads = threading.enumerate()
        result = []
        event = threading.Event()
        def _writer():
            current = threading.currentThread()
            if current not in previousThreads:
                result.append(current)
            event.set()
        writer = ThreadedFileWriter(BytesIO(), reactor)
        writer._writer = _writer
        writer.startService()
        event.wait()
        self.assertTrue(result)
        # Make sure thread is dead so it doesn't die half way through another
        # test:
        result[0].join(5)

    def test_stopServiceStopsThread(self):
        """
        L{ThreadedFileWriter.stopService} stops the writer thread.
        """
        previousThreads = set(threading.enumerate())
        writer = ThreadedFileWriter(BytesIO(), reactor)
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


    def test_write(self):
        """
        Messages passed to L{ThreadedFileWriter.write} are then written by the
        writer thread with a newline added.
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
        Messages passed to L{ThreadedFileWriter.write} are then written by the
        writer thread with a newline added to files that accept unicode.
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


    def test_stopServiceFinishesWriting(self):
        """
        L{ThreadedFileWriter.stopService} stops the writer thread, but only after
        all queued writes are written out.
        """
        f = BlockingFile()
        writer = ThreadedFileWriter(f, reactor)
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
        L{ThreadedFileWriter.stopService} returns a L{Deferred} that fires only
        after the thread has shut down.
        """
        f = BlockingFile()
        writer = ThreadedFileWriter(f, reactor)
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


    def test_stopServiceClosesFile(self):
        """
        L{ThreadedFileWriter.stopService} closes the file.
        """
        f = BytesIO()
        writer = ThreadedFileWriter(f, reactor)
        writer.startService()
        d = writer.stopService()
        def done(_):
            self.assertTrue(f.closed)
        d.addCallback(done)
        return d


    def test_noChangeToIOThread(self):
        """
        Running a L{ThreadedFileWriter} doesn't modify the Twisted registered IO
        thread.
        """
        writer = ThreadedFileWriter(BytesIO(), reactor)
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
        L{ThreadedFileWriter.startService} registers itself as an Eliot log
        destination.
        """
        f = BlockingFile()
        writer = ThreadedFileWriter(f, reactor)
        writer.startService()
        Logger().write({"x": "abc"})
        d = writer.stopService()
        d.addCallback(lambda _: self.assertIn(b"abc", f.getvalue()))
        return d


    def test_stopServiceUnregistersDestination(self):
        """
        L{ThreadedFileWriter.stopService} unregisters itself as an Eliot log
        destination.
        """
        writer = ThreadedFileWriter(BytesIO(), reactor)
        writer.startService()
        d = writer.stopService()
        d.addCallback(lambda _: removeDestination(writer))
        return self.assertFailure(d, ValueError)
