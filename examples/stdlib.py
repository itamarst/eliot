"""
Example of routing standard library logging to Eliot.

The assumption is you have legacy logging using stdlib, and are switching over
to Eliot.
"""

import logging
import sys

from eliot.stdlib import EliotHandler
from eliot import start_action, to_file

# A Logger left over from before switch to Eliot
LEGACY_LOGGER = logging.Logger("mypackage")


def do_a_thing(i):
    with start_action(action_type="mypackage:do_a_thing"):
        # run your business logic....
        if i == 3:
            LEGACY_LOGGER.error("The number 3 is a bad number, don't use it.")
            raise ValueError("I hate the number 3")


def main():
    with start_action(action_type="mypackage:main"):
        for i in [1, 3]:
            try:
                do_a_thing(i)
            except ValueError:
                LEGACY_LOGGER.info("Number {} was rejected.".format(i))


if __name__ == '__main__':
    # Hook up stdlib logging to Eliot:
    LEGACY_LOGGER.addHandler(EliotHandler())
    # Write Eliot logs to stdout:
    to_file(sys.stdout)
    # Run the code:
    main()
