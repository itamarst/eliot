"""
Output an Eliot message to a log file using the threaded log writer.
"""

from twisted.internet.task import react

from eliot.logwriter import ThreadedWriter
from eliot import log_message, FileDestination


def main(reactor):
    print("Logging to example-eliot.log...")
    logWriter = ThreadedWriter(
        FileDestination(file=open("example-eliot.log", "ab")), reactor)

    # Manually start the service, which will add it as a
    # destination. Normally we'd register ThreadedWriter with the usual
    # Twisted Service/Application infrastructure.
    logWriter.startService()

    # Log a message:
    log_message(message_type="test", value="hello", another=1)

    # Manually stop the service.
    done = logWriter.stopService()
    return done


if __name__ == '__main__':
    react(main, [])
