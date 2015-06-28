"""
Output a few Eliot message to standard out.
"""
from __future__ import unicode_literals

import sys
import time

from eliot import Message, to_file
to_file(sys.stdout)


def main():
    Message.log(value="hello", another=1)
    time.sleep(0.2)
    Message.log(value="goodbye", another=2)


if __name__ == '__main__':
    main()
