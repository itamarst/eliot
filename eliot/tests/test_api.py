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


    def test_addGlobalFields(self):
        """
        L{eliot.addGlobalFields} calls the corresponding method on the
        L{Destinations} attached to L{Logger}.
        """
        self.assertEqual(eliot.addGlobalFields,
                         Logger._destinations.addGlobalFields)



class PEP8Tests(TestCase):
    """
    Tests for the PEP 8 variant of the the public API.
    """
    def test_add_destination(self):
        """
        L{eliot.addDestionation} is the same as L{eliot.add_destination}.
        """
        self.assertIs(eliot.add_destination, eliot.addDestination)


    def test_remove_destination(self):
        """
        L{eliot.removeDestionation} is the same as L{eliot.remove_destination}.
        """
        self.assertIs(eliot.remove_destination, eliot.removeDestination)


    def test_add_global_fields(self):
        """
        L{eliot.add_global_fields} is the same as L{eliot.addGlobalFields}.
        """
        self.assertIs(eliot.add_global_fields, eliot.addGlobalFields)


    def test_write_traceback(self):
        """
        L{eliot.writeTraceback} is the same as L{eliot.write_traceback}.
        """
        self.assertIs(eliot.write_traceback, eliot.writeTraceback)


    def test_write_failure(self):
        """
        L{eliot.writeFailure} is the same as L{eliot.write_failure}.
        """
        self.assertIs(eliot.write_failure, eliot.writeFailure)


    def test_start_task(self):
        """
        L{eliot.startTask} is the same as L{eliot.start_task}.
        """
        self.assertIs(eliot.start_task, eliot.startTask)


    def test_start_action(self):
        """
        L{eliot.startAction} is the same as L{eliot.start_action}.
        """
        self.assertIs(eliot.start_action, eliot.startAction)
