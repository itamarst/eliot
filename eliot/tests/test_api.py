"""
Tests for the public API exposed by L{eliot}.
"""

from __future__ import unicode_literals

from unittest import TestCase

from .._output import Logger
import eliot


class PublicAPITests(TestCase):
    """
    Tests for the public API.
    """
    def test_addDestination(self):
        """
        L{eliot.addDestination} adds destinations to the L{Destinations}
        attached to L{Logger}.
        """
        self.assertEqual(eliot.addDestination, Logger._destinations.add)


    def test_removeDestination(self):
        """
        L{eliot.addDestination} removes destinations from the L{Destinations}
        attached to L{Logger}.
        """
        self.assertEqual(eliot.removeDestination, Logger._destinations.remove)
