"""
Output a few Eliot message to standard out.
"""
from __future__ import unicode_literals

import sys
import time
import json

from eliot import Message, Logger, addDestination

addDestination(lambda message: sys.stdout.write(json.dumps(message) + "\n"))
_logger = Logger()


def main():
    Message.new(value="hello", another=1).write(_logger)
    time.sleep(0.2)
    Message.new(value="goodbye", another=2).write(_logger)


if __name__ == '__main__':
    main()
