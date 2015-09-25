"""
Tests for C{{eliot.prettyprint}}.
"""

from __future__ import unicode_literals

from unittest import TestCase

from ..prettyprint import pretty_print


class FormattingTests(TestCase):
    """
    Tests for L{{pretty_print}}.
    """
    def test_message(self):
        """
        A typed message is printed as expected.
        """
        message = {"timestamp": 1443193754,
                   "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
                   "message_type": "messagey",
                   "task_level": [1, 2],
                   "keys": [123, 456]}
        self.assertEqual(
            pretty_print(message),
            """\
8c668cde-235b-4872-af4e-caea524bd1c0@/1/2
2015-09-25T15:09:14Z
  message_type: messagey
  keys: [123, 456]
""")

    def test_untyped_message(self):
        """
        A message with no type is printed as expected.
        """
        message = {"timestamp": 1443193754,
                   "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
                   "task_level": [1],
                   "key": 1234,
                   "abc": "def"}
        print repr(pretty_print(message))
        self.assertEqual(
            pretty_print(message),
            """\
8c668cde-235b-4872-af4e-caea524bd1c0@/1
2015-09-25T15:09:14Z
  abc: def
  key: 1234
""")

    def test_action(self):
        """
        An action message is printed as expected.
        """
        message = {"task_uuid": "8bc6ded2-446c-4b6d-abbc-4f21f1c9a7d8",
                   "place": "Statue #1",
                   "task_level": [2, 2, 2, 1],
                   "action_type": "visited",
                   "timestamp": 1443193958.0,
                   "action_status": "started"}
        self.assertEqual(
            pretty_print(message),
            """\
8bc6ded2-446c-4b6d-abbc-4f21f1c9a7d8@/2/2/2/1
2015-09-25T15:12:38Z
  action_type: visited
  action_status: started
  place: Statue #1
""")

    def test_linebreaks_stripped(self):
        """
        Linebreaks are stripped from end of string values.
        """
        message = {"timestamp": 1443193754,
                   "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
                   "task_level": [1],
                   "key": "hello\n\n\n"}
        print pretty_print(message)
        self.assertEqual(
            pretty_print(message),
            """\
8c668cde-235b-4872-af4e-caea524bd1c0@/1
2015-09-25T15:09:14Z
  key: hello
""")

    def test_multi_line(self):
        """
        Multiple line values are indented nicely.
        """
        message = {"timestamp": 1443193754,
                   "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
                   "task_level": [1],
                   "key": "hello\nthere\nmonkeys!",
                   "more": "stuff"}
        print pretty_print(message)
        self.assertEqual(
            pretty_print(message),
            """\
8c668cde-235b-4872-af4e-caea524bd1c0@/1
2015-09-25T15:09:14Z
  key: hello
       there
       monkeys!
  more: stuff
""")
