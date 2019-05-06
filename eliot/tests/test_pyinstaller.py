"""Test for pyinstaller compatibility."""

from __future__ import absolute_import

from unittest import TestCase, SkipTest
from tempfile import mkdtemp, NamedTemporaryFile
from subprocess import check_call, CalledProcessError
import os

from six import PY2

if PY2:
    FileNotFoundError = OSError


class PyInstallerTests(TestCase):
    """Make sure PyInstaller doesn't break Eliot."""

    def setUp(self):
        try:
            check_call(["pyinstaller", "--help"])
        except (CalledProcessError, FileNotFoundError):
            raise SkipTest("Can't find pyinstaller.")

    def test_importable(self):
        """The Eliot package can be imported inside a PyInstaller packaged binary."""
        output_dir = mkdtemp()
        with NamedTemporaryFile(mode="w") as f:
            f.write("import eliot; import eliot.prettyprint\n")
            f.flush()
            check_call(
                [
                    "pyinstaller",
                    "--distpath",
                    output_dir,
                    "-F",
                    "-n",
                    "importeliot",
                    f.name,
                ]
            )
        check_call([os.path.join(output_dir, "importeliot")])
