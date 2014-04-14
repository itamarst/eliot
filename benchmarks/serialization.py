"""
Benchmark of message serialization.

The goal here is to mostly focus on performance of serialization, in a vaguely
realistic manner. That is, mesages are logged in context of a message with a
small number of fields.
"""

from __future__ import unicode_literals

import time

from eliot import Logger, MessageType, Field, ActionType

def _ascii(s):
    return s.decode("ascii")


F1 = Field.forTypes("integer", [int], "")
F2 = Field("string", _ascii, "")
F3 = Field("string2", _ascii, "")
F4 = Field.forTypes("list", [list], "list of integers")

M = MessageType("system:message", [F1, F2, F3, F4], "description")
A = ActionType("action", [], [], [], "desc")

log = Logger()

N = 100000

def run():
    start = time.time()
    with A(log):
        for i in xrange(N):
            m = M(integer=3, string=b"abcdeft", string2="dgsjdlkgjdsl", list=[1, 2, 3, 4])
            m.write(log)
    end = time.time()
    print "%.6f per message" % ((end - start) / N,)
    print "%s messages/sec" % (int(N / (end-start)),)

if __name__ == '__main__':
    run()
