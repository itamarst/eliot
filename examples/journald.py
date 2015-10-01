"""
Write some logs to journald.
"""

from __future__ import print_function

from eliot import Message, start_action, add_destination
from eliot.journald import JournaldDestination

add_destination(JournaldDestination())


def divide(a, b):
    with start_action(action_type="divide", a=a, b=b):
        return a / b

print(divide(10, 2))
Message.log(message_type="inbetween")
print(divide(10, 0))
