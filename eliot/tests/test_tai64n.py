"""
Tests for L{eliot.tai64n}.
"""

from __future__ import unicode_literals

import errno
import time
import subprocess
from unittest import TestCase, SkipTest

from ..tai64n import encode, decode


class CodecTests(TestCase):
    """
    Tests for L{encode} and L{decode}.
    """
    def test_encode(self):
        """
        L{encode} encodes timestamps in TAI64N format.
        """
        t = 1387299889.153187625
        self.assertEqual(encode(t), "@4000000052b0843b092174b9")


    def test_decode(self):
        """
        L{decode} decodes timestamps from TAI64N format.
        """
        t = time.time()
        self.assertAlmostEqual(t, decode(encode(t)), 9)



class FunctionalTests(TestCase):
    """
    Functional tests for L{encode}.
    """
    def test_encode(self):
        """
        The daemontools tai64nlocal tool can correctly decode timestamps output
        by L{encode}.
        """
        try:
            process = subprocess.Popen(["tai64nlocal"], bufsize=4096,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE)
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise SkipTest("This test requires the daemontools package")
            else:
                raise
        # Because of limitations of the time libraries tai64nlocal uses we
        # apparently can't verify beyond this level of accuracy.
        timestamp = int(time.time()) + 0.12345
        process.stdin.write((encode(timestamp) + "\n").encode("ascii"))
        process.stdin.close()
        decodedToLocalTime = process.stdout.read().strip()
        self.assertEqual(time.strftime("%Y-%m-%d %H:%M:%S.12345",
                                       time.localtime(timestamp)).encode("ascii"),
                         decodedToLocalTime[:25])
