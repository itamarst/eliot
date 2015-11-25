"""
Error-handling utility code.
"""

from __future__ import unicode_literals

from inspect import getmro


class ErrorExtraction(object):
    """
    Extract fields from exceptions for failed-action messages.

    @ivar registry: Map exception class to function that extracts fields.
    """
    def __init__(self):
        self.registry = {}

    def extract_fields_for_failures(self, exception_class, extracter):
        """
        Register a function that converts exceptions to fields.

        @param exception_class: Class to register for.

        @param extracter: Single-argument callable that takes an exception
            of the given class (or a subclass) and returns a dictionary,
            fields to include in a failed action message.
        """
        self.registry[exception_class] = extracter

    def get_fields_for_exception(self, logger, exception):
        """
        Given an exception instance, return fields to add to the failed action
        message.

        @param logger: ``ILogger`` currently being used.
        @param exception: An exception instance.

        @return: Dictionary with fields to include.
        """
        for klass in getmro(exception.__class__):
            if klass in self.registry:
                extracter = self.registry[klass]
                try:
                    return extracter(exception)
                except:
                    from ._traceback import writeTraceback
                    writeTraceback(logger)
                    return {}
        return {}

_error_extraction = ErrorExtraction()
extract_fields_for_failures = _error_extraction.extract_fields_for_failures

# Default handler for OSError and IOError by registered EnvironmentError:
extract_fields_for_failures(EnvironmentError, lambda e: {"errno": e.errno})
