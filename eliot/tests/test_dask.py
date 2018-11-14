"""Tests for eliot.dask."""

from unittest import TestCase, skipUnless

try:
    import dask
    from dask.bag import from_sequence
except ImportError:
    dask = None
else:
    from eliot.dask import compute_with_trace, _RunWithEliotContext, _add_logging


@skipUnless(dask, "Dask not available.")
class DaskTests(TestCase):
    """Tests for end-to-end functionality."""

    def test_compute(self):
        """compute_with_trace() runs the same logic as compute()."""
        bag = from_sequence([1, 2, 3])
        bag = bag.map(lambda x: x * 7).map(lambda x: x * 4)
        bag = bag.fold(lambda x, y: x + y)
        self.assertEqual(dask.compute(bag), compute_with_trace(bag))
