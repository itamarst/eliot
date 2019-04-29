"""
Benchmark of message serialization.

The goal here is to mostly focus on performance of serialization, in a vaguely
realistic manner. That is, mesages are logged in context of a message with a
small number of fields.
"""

from __future__ import unicode_literals

import time

from eliot import Message, start_action, to_file

# Ensure JSON serialization is part of benchmark:
to_file(open("/dev/null", "w"))

N = 10000


def run():
    start = time.time()
    for i in range(N):
        with start_action(action_type="my_action"):
            with start_action(action_type="my_action2"):
                Message.log(
                    message_type="my_message",
                    integer=3, string=b"abcdeft", string2="dgsjdlkgjdsl",
                    list=[1, 2, 3, 4])
    end = time.time()

    # Each iteration has 5 messages: start/end of my_action, start/end of
    # my_action2, and my_message.
    print("%.6f per message" % ((end - start) / (N * 5),))
    print("%s messages/sec" % (int(N / (end-start)),))


if __name__ == '__main__':
    run()
