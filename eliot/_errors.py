"""
Error-handling utility code.
"""

from inspect import getmro


class ErrorExtraction(object):
    """
    Extract fields from exceptions for failed-action messages.

    @ivar registry: Map exception class to function that extracts fields.
    """

    def __init__(self):
        self.registry = {}

    def register_exception_extractor(self, exception_class, extractor):
        """
        Register a function that converts exceptions to fields.

        @param exception_class: Class to register for.

        @param extractor: Single-argument callable that takes an exception
            of the given class (or a subclass) and returns a dictionary,
            fields to include in a failed action message.
        """
        self.registry[exception_class] = extractor

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
                extractor = self.registry[klass]
                try:
                    return extractor(exception)
                except:
                    from ._traceback import write_traceback

                    write_traceback(logger)
                    return {}
        return {}


_error_extraction = ErrorExtraction()
register_exception_extractor = _error_extraction.register_exception_extractor
get_fields_for_exception = _error_extraction.get_fields_for_exception

# Default handler for OSError and IOError by registered EnvironmentError:
register_exception_extractor(EnvironmentError, lambda e: {"errno": e.errno})
