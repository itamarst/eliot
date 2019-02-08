"""
Benchmark of message serialization.

The goal here is to mostly focus on performance of serialization, in a vaguely
realistic manner. That is, mesages are logged in context of a message with a
small number of fields.
"""

import time

from eliot import Message, start_action

N = 100000


def run():
    start = time.time()
    with start_action(action_type="my_action"):
        for i in range(N):
            Message.log(
                action_type="my_action",
                integer=3, string=b"abcdeft", string2="dgsjdlkgjdsl", list=[1, 2, 3, 4])
    end = time.time()
    print("%.6f per message" % ((end - start) / N,))
    print("%s messages/sec" % (int(N / (end-start)),))


if __name__ == '__main__':
    run()
