"""
Tests for L{eliot.filter}.
"""
from __future__ import unicode_literals

from six import PY3

import sys
import time
if PY3:
    from .. import _py3json as json
else:
    import json
from unittest import TestCase
from datetime import datetime
from io import BytesIO
import inspect

from ..filter import EliotFilter, main, USAGE
from .. import tai64n


class EliotFilterTests(TestCase):
    """
    Tests for L{EliotFilter}.
    """
    def test_expression(self):
        """
        For each item in the incoming sequence L{EliotFilter.run} calls
        L{EliotFilter._evaluate} with the item decoded from JSON, and writes the
        result to the output file as JSON.
        """
        f = BytesIO()
        efilter = EliotFilter("J", [b'"abcd"', b"[1, 2]"], f)
        efilter._evaluate = lambda expr: {"x": len(expr), "orig": expr}
        self.assertEqual(f.getvalue(), b"")
        efilter.run()
        self.assertEqual(f.getvalue(),
                         json.dumps({"x": 4, "orig": "abcd"}) + b"\n" +
                         json.dumps({"x": 2, "orig": [1, 2]}) +  b'\n')


    def evaluateExpression(self, expr, message):
        """
        Render a single message with the given expression using
        L{EliotFilter._evaluate}.
        """
        efilter = EliotFilter(expr, [], BytesIO())
        return efilter._evaluate(message)


    def test_J(self):
        """
        The expression has access to the decoded JSON message as C{J} in its
        locals.
        """
        result = self.evaluateExpression("J['a']", {"a": 123})
        self.assertEqual(result, 123)


    def test_timestamp(self):
        """
        The timestamp field in C{J} is decoded to a L{datetime}.
        """
        timestamp = int(time.time())
        dt = datetime.utcfromtimestamp(timestamp)
        message = {"timestamp": tai64n.encode(timestamp)}
        result = self.evaluateExpression("list(J['timestamp'].utctimetuple())",
                                         message)
        self.assertEqual(result, list(dt.utctimetuple()))


    def test_otherLocals(self):
        """
        The expression has access to L{datetime} and L{timedelta} in its built-ins.
        """
        result = self.evaluateExpression(
            "isinstance(datetime.utcnow() - datetime.utcnow(), timedelta)", {})
        self.assertEqual(result, True)


    def test_datetimeSerialization(self):
        """
        Any L{datetime} in result will be serialized using L{datetime.isoformat}.
        """
        timestamp = int(time.time())
        dt = datetime.utcfromtimestamp(timestamp)
        message = json.dumps({"timestamp": tai64n.encode(timestamp)})
        f = BytesIO()
        EliotFilter("J", [message], f).run()
        expected = json.dumps({"timestamp": dt.isoformat()}) + b"\n"
        self.assertEqual(f.getvalue(), expected)


    def test_SKIP(self):
        """
        A result of C{SKIP} indicates nothing should be output.
        """
        f = BytesIO()
        EliotFilter("SKIP", [b'{"a": 123}'], f).run()
        self.assertEqual(f.getvalue(), b"")



class FakeSys(object):
    """
    A fake L{sys} module.
    """
    def __init__(self, argv, stdinBytes):
        """
        @param argv: List of command-line arguments.

        @param stdinBytes: C{bytes} that are readable from stdin.
        """
        self.argv = argv
        self.stdin = BytesIO(stdinBytes)
        self.stdout = BytesIO()
        self.stderr = BytesIO()



class MainTests(TestCase):
    """
    Test cases for L{main}.
    """
    def test_default(self):
        """
        By default L{main} uses information from L{sys}.
        """
        self.assertEqual(inspect.getargspec(main).defaults, (sys,))


    def test_stdinOut(self):
        """
        L{main} reads from the C{stdin} attribute of the given C{sys} equivalent,
        and writes rendered expressions to the C{stdout} attribute.
        """
        sys = FakeSys(["eliotfilter", "J[0]"], b"[1, 2]\n[4, 5]\n")
        main(sys)
        self.assertEqual(sys.stdout.getvalue(), b"1\n4\n")


    def test_success(self):
        """
        A successful run returns C{0}.
        """
        sys = FakeSys(["eliotfilter", "J[0]"], b"[1, 2]\n[4, 5]\n")
        result = main(sys)
        self.assertEqual(result, 0)


    def test_noArguments(self):
        """
        If given no arguments, usage documentation is printed to stderr and C{1} is
        returned.
        """
        sys = FakeSys(["eliotfilter"], b"")
        result = main(sys)
        self.assertEqual(sys.stderr.getvalue(), USAGE)
        self.assertEqual(result, 1)
