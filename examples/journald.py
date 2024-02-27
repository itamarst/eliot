"""
Write some logs to journald.
"""


from eliot import log_message, start_action, add_destinations
from eliot.journald import JournaldDestination

add_destinations(JournaldDestination())


def divide(a, b):
    with start_action(action_type="divide", a=a, b=b):
        return a / b

print(divide(10, 2))
log_message(message_type="inbetween")
print(divide(10, 0))
