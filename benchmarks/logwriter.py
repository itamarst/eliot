"""
A benchmark for eliot.logwriter.
"""

import tempfile
import time

from twisted.internet.task import react
from twisted.python.filepath import FilePath

from eliot.logwriter import ThreadedFileWriter


LENGTH = 100
MESSAGES = 100000


def main(reactor):
    print("Message size: %d bytes   Num messages: %d" % (LENGTH, MESSAGES))
    message = b"a" * LENGTH
    fp = FilePath(tempfile.mktemp())
    writer = ThreadedFileWriter(fp.open("ab"), reactor)
    writer.startService()

    start = time.time()
    for i in range(MESSAGES):
        writer(message)
    d = writer.stopService()

    def done(_):
        elapsed = time.time() - start
        kbSec = (LENGTH * MESSAGES) / (elapsed * 1024)
        messagesSec = MESSAGES / elapsed
        print("messages/sec: %s   KB/sec: %s" % (messagesSec, kbSec))
    d.addCallback(done)

    def cleanup(result):
        fp.restat()
        print()
        print("File size: ", fp.getsize())
        fp.remove()
    d.addBoth(cleanup)
    return d


if __name__ == '__main__':
    react(main, [])
