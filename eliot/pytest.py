"""Plugins for py.test."""

import json

import pytest

from .testutil import _capture_logs
from .json import EliotJSONEncoder


@pytest.fixture
def eliot_logs(request):
    """
    Capture log messages for the duration of the test.

        1. The fixture object is a L{eliot.testutil.TestingDestination}.

        2. All messages logged during the test are validated at the end of
           the test.

        3. Any unflushed logged tracebacks will cause the test to fail.  If you
           expect a particular tracekbac, you can flush it by calling
           C{remove_expected_tracebacks} on the C{TestingDestination} instance.
    """

    def logs_for_pyttest(encode=EliotJSONEncoder().encode, decode=json.loads):
        return _capture_logs(request.addfinalizer, encode, decode)


__all__ = ["eliot_logs"]
