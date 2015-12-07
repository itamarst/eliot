#!/usr/bin/env python

"""
Example of an Eliot action context spanning multiple threads.
"""

from __future__ import unicode_literals

from threading import Thread
from sys import stdout

from eliot import to_file, preserve_context, start_action
to_file(stdout)


def add_in_thread(x, y):
    with start_action(action_type="in_thread", x=x, y=y) as context:
        context.add_success_fields(result=x+y)


with start_action(action_type="main_thread"):
    # Preserve Eliot context and restore in new thread:
    thread = Thread(target=preserve_context(add_in_thread),
                    kwargs={"x": 3, "y": 4})
    thread.start()
    # Wait for the thread to exit:
    thread.join()

