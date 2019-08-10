"""
Tests for C{eliot.prettyprint}.
"""

from unittest import TestCase
from subprocess import check_output, Popen, PIPE
from collections import OrderedDict
from datetime import datetime

from pyrsistent import pmap

from .._bytesjson import dumps
from ..prettyprint import pretty_format, compact_format, REQUIRED_FIELDS

SIMPLE_MESSAGE = {
    "timestamp": 1443193754,
    "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
    "message_type": "messagey",
    "task_level": [1, 2],
    "keys": [123, 456],
}

UNTYPED_MESSAGE = {
    "timestamp": 1443193754,
    "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
    "task_level": [1],
    "key": 1234,
    "abc": "def",
}


class FormattingTests(TestCase):
    """
    Tests for L{pretty_format}.
    """

    def test_message(self):
        """
        A typed message is printed as expected.
        """
        self.assertEqual(
            pretty_format(SIMPLE_MESSAGE),
            """\
8c668cde-235b-4872-af4e-caea524bd1c0 -> /1/2
2015-09-25T15:09:14Z
  message_type: 'messagey'
  keys: [123, 456]
""",
        )

    def test_untyped_message(self):
        """
        A message with no type is printed as expected.
        """
        self.assertEqual(
            pretty_format(UNTYPED_MESSAGE),
            """\
8c668cde-235b-4872-af4e-caea524bd1c0 -> /1
2015-09-25T15:09:14Z
  abc: 'def'
  key: 1234
""",
        )

    def test_action(self):
        """
        An action message is printed as expected.
        """
        message = {
            "task_uuid": "8bc6ded2-446c-4b6d-abbc-4f21f1c9a7d8",
            "place": "Statue #1",
            "task_level": [2, 2, 2, 1],
            "action_type": "visited",
            "timestamp": 1443193958.0,
            "action_status": "started",
        }
        self.assertEqual(
            pretty_format(message),
            """\
8bc6ded2-446c-4b6d-abbc-4f21f1c9a7d8 -> /2/2/2/1
2015-09-25T15:12:38Z
  action_type: 'visited'
  action_status: 'started'
  place: 'Statue #1'
""",
        )

    def test_multi_line(self):
        """
        Multiple line values are indented nicely.
        """
        message = {
            "timestamp": 1443193754,
            "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
            "task_level": [1],
            "key": "hello\nthere\nmonkeys!\n",
            "more": "stuff",
        }
        self.assertEqual(
            pretty_format(message),
            """\
8c668cde-235b-4872-af4e-caea524bd1c0 -> /1
2015-09-25T15:09:14Z
  key: 'hello
     |  there
     |  monkeys!
     |  '
  more: 'stuff'
""",
        )

    def test_tabs(self):
        """
        Tabs are formatted as tabs, not quoted.
        """
        message = {
            "timestamp": 1443193754,
            "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
            "task_level": [1],
            "key": "hello\tmonkeys!",
        }
        self.assertEqual(
            pretty_format(message),
            """\
8c668cde-235b-4872-af4e-caea524bd1c0 -> /1
2015-09-25T15:09:14Z
  key: 'hello	monkeys!'
""",
        )

    def test_structured(self):
        """
        Structured field values (e.g. a dictionary) are formatted in a helpful
        manner.
        """
        message = {
            "timestamp": 1443193754,
            "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
            "task_level": [1],
            "key": {"value": 123, "another": [1, 2, {"more": "data"}]},
        }
        self.assertEqual(
            pretty_format(message),
            """\
8c668cde-235b-4872-af4e-caea524bd1c0 -> /1
2015-09-25T15:09:14Z
  key: {'another': [1, 2, {'more': 'data'}],
     |  'value': 123}
""",
        )

    def test_microsecond(self):
        """
        Microsecond timestamps are rendered in the output.
        """
        message = {
            "timestamp": 1443193754.123455,
            "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
            "task_level": [1],
        }
        self.assertEqual(
            pretty_format(message),
            """\
8c668cde-235b-4872-af4e-caea524bd1c0 -> /1
2015-09-25T15:09:14.123455Z
""",
        )

    def test_compact(self):
        """
        The compact mode does everything on a single line, including
        dictionaries and multi-line messages.
        """
        message = {
            "timestamp": 1443193754,
            "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
            "task_level": [1],
            "key": OrderedDict([("value", 123), ("another", [1, 2, {"more": "data"}])]),
            "multiline": "hello\n\tthere!\nabc",
        }
        self.assertEqual(
            compact_format(message),
            r'8c668cde-235b-4872-af4e-caea524bd1c0/1 2015-09-25T15:09:14Z key={"value":123,"another":[1,2,{"more":"data"}]} multiline="hello\n\tthere!\nabc"',
        )

    def test_local(self):
        """
        Timestamps can be generated in local timezone.
        """
        message = {
            "timestamp": 1443193754,
            "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
            "task_level": [1],
        }
        expected = datetime.fromtimestamp(1443193754).isoformat(sep="T")
        self.assertIn(expected, pretty_format(message, True))
        self.assertIn(expected, compact_format(message, True))


class CommandLineTests(TestCase):
    """
    Tests for the command-line tool.
    """

    def test_help(self):
        """
        C{--help} prints out the help text and exits.
        """
        result = check_output(["eliot-prettyprint", "--help"])
        self.assertIn(b"Convert Eliot messages into more readable", result)

    def write_and_read(self, lines, extra_args=()):
        """
        Write the given lines to the command-line on stdin, return stdout.

        @param lines: Sequences of lines to write, as bytes, and lacking
            new lines.
        @return: Unicode-decoded result of subprocess stdout.
        """
        process = Popen(
            [b"eliot-prettyprint"] + list(extra_args), stdin=PIPE, stdout=PIPE
        )
        process.stdin.write(b"".join(line + b"\n" for line in lines))
        process.stdin.close()
        result = process.stdout.read().decode("utf-8")
        process.stdout.close()
        return result

    def test_output(self):
        """
        Lacking command-line arguments the process reads JSON lines from stdin
        and writes out a pretty-printed version.
        """
        messages = [SIMPLE_MESSAGE, UNTYPED_MESSAGE, SIMPLE_MESSAGE]
        stdout = self.write_and_read(map(dumps, messages))
        self.assertEqual(
            stdout, "".join(pretty_format(message) + "\n" for message in messages)
        )

    def test_compact_output(self):
        """
        In compact mode, the process reads JSON lines from stdin and writes out
        a pretty-printed compact version.
        """
        messages = [SIMPLE_MESSAGE, UNTYPED_MESSAGE, SIMPLE_MESSAGE]
        stdout = self.write_and_read(map(dumps, messages), [b"--compact"])
        self.assertEqual(
            stdout, "".join(compact_format(message) + "\n" for message in messages)
        )

    def test_local_timezone(self):
        """
        Local timezones are used if --local-timezone is given.
        """
        message = {
            "timestamp": 1443193754,
            "task_uuid": "8c668cde-235b-4872-af4e-caea524bd1c0",
            "task_level": [1],
        }
        expected = datetime.fromtimestamp(1443193754).isoformat(sep="T")
        stdout = self.write_and_read(
            [dumps(message)], [b"--compact", b"--local-timezone"]
        )
        self.assertIn(expected, stdout)
        stdout = self.write_and_read(
            [dumps(message)], [b"--compact", b"--local-timezone"]
        )
        self.assertIn(expected, stdout)

    def test_not_json_message(self):
        """
        Non-JSON lines are not formatted.
        """
        not_json = b"NOT JSON!!"
        lines = [dumps(SIMPLE_MESSAGE), not_json, dumps(UNTYPED_MESSAGE)]
        stdout = self.write_and_read(lines)
        self.assertEqual(
            stdout,
            "{}\nNot JSON: {}\n\n{}\n".format(
                pretty_format(SIMPLE_MESSAGE),
                str(not_json),
                pretty_format(UNTYPED_MESSAGE),
            ),
        )

    def test_missing_required_field(self):
        """
        Non-Eliot JSON messages are not formatted.
        """
        base = pmap(SIMPLE_MESSAGE)
        messages = [dumps(dict(base.remove(field))) for field in REQUIRED_FIELDS] + [
            dumps(SIMPLE_MESSAGE)
        ]
        stdout = self.write_and_read(messages)
        self.assertEqual(
            stdout,
            "{}{}\n".format(
                "".join(
                    "Not an Eliot message: {}\n\n".format(msg) for msg in messages[:-1]
                ),
                pretty_format(SIMPLE_MESSAGE),
            ),
        )
