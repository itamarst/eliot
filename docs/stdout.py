"""
Output a few Eliot message to standard out.
"""
from __future__ import unicode_literals

import sys
import time

from eliot import Message, addDestination


def stdout(message):
    sys.stdout.write(message + "\n")
addDestination(stdout)


Message.write(value="hello", another=1)
time.sleep(0.2)
Message.write(value="goodbye", another=2)
