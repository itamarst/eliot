"""
Output an Eliot message to a log file using the threaded log writer.
"""
from __future__ import unicode_literals, print_function

from twisted.internet.task import react

from eliot.logwriter import ThreadedFileWriter
from eliot import Message


def main(reactor):
    print("Logging to example-eliot.log...")
    logWriter = ThreadedFileWriter(open("example-eliot.log", "ab"), reactor)

    # Manually start the service, which will add it as a
    # destination. Normally we'd register ThreadedFileWriter with the usual
    # Twisted Service/Application infrastructure.
    logWriter.startService()

    # Log a message:
    Message.log(value="hello", another=1)

    # Manually stop the service.
    done = logWriter.stopService()
    return done


if __name__ == '__main__':
    react(main, [])
