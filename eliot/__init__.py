"""
Eliot: Logging for Complex & Distributed Systems.
"""
from warnings import warn
from sys import version_info

# Enable asyncio contextvars support in Python 3.5/3.6:
if version_info < (3, 7):
    # On Python 3.5.2 and earlier, some of the necessary attributes aren't exposed:
    if version_info < (3, 5, 3):
        raise RuntimeError(
            "This version of Eliot doesn't work on Python 3.5.2 or earlier. "
            "Either upgrade to a newer version of Python (e.g. on Ubuntu 16.04 "
            "you can use the deadsnakes PPA to get Python 3.6), or pin Eliot "
            "to version 1.7."
        )
    import aiocontextvars

    dir(aiocontextvars)  # pacify pyflakes
    del aiocontextvars

# Expose the public API:
from ._message import Message
from ._action import (
    start_action,
    startTask,
    Action,
    preserve_context,
    current_action,
    log_call,
)
from ._output import ILogger, Logger, MemoryLogger, to_file, FileDestination
from ._validation import Field, fields, MessageType, ActionType, ValidationError
from ._traceback import write_traceback, writeFailure
from ._errors import register_exception_extractor
from ._version import get_versions

# Backwards compatibility:
def add_destination(destination):
    warn(
        "add_destination is deprecated since 1.1.0. " "Use add_destinations instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    Logger._destinations.add(destination)


# Backwards compatibility:
def use_asyncio_context():
    warn(
        "This function is no longer as needed as of Eliot 1.8.0.",
        DeprecationWarning,
        stacklevel=2,
    )


# Backwards compatibilty:
addDestination = add_destination
removeDestination = Logger._destinations.remove
addGlobalFields = Logger._destinations.addGlobalFields
writeTraceback = write_traceback
startAction = start_action

# PEP 8 variants:
start_task = startTask
write_failure = writeFailure
add_destinations = Logger._destinations.add
remove_destination = removeDestination
add_global_fields = addGlobalFields

# Backwards compatibility for old versions of eliot-tree, which rely on
# eliot._parse:
def _parse_compat():
    # Force eliot.parse to be imported in way that works with old Python:
    from .parse import Parser

    del Parser
    import sys

    sys.modules["eliot._parse"] = sys.modules["eliot.parse"]
    return sys.modules["eliot.parse"]


_parse = _parse_compat()
del _parse_compat


__all__ = [
    "Message",
    "writeTraceback",
    "writeFailure",
    "startAction",
    "startTask",
    "Action",
    "preserve_context",
    "Field",
    "fields",
    "MessageType",
    "ActionType",
    "ILogger",
    "Logger",
    "MemoryLogger",
    "addDestination",
    "removeDestination",
    "addGlobalFields",
    "FileDestination",
    "register_exception_extractor",
    "current_action",
    "use_asyncio_context",
    "ValidationError",
    # PEP 8 variants:
    "write_traceback",
    "write_failure",
    "start_action",
    "start_task",
    "add_destination",
    "add_destinations",
    "remove_destination",
    "add_global_fields",
    "to_file",
    "log_call",
    "__version__",
    # Backwards compat for eliot-tree:
    "_parse",
]


__version__ = get_versions()["version"]
del get_versions
