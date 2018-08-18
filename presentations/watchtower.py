import sys

from eliot import start_action, to_file, Message
to_file(sys.stdout)


rider1 = "Alice"
rider2 = "Bob"
wildcat = "Whiskers the Wildcat"


with start_action(action_type="outside", weather="cold",
                  location="distance"):
    with start_action(action_type="approach",
                      who=[rider1, rider2]):
        with start_action(action_type="growl", who=wildcat):
            pass
    Message.log(message_type="wind:howl")
