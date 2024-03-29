"""
Eliot: Logging for Complex & Distributed Systems.
"""

from warnings import warn

# Expose the public API:
from ._message import Message
from ._action import (
    start_action,
    startTask,
    Action,
    preserve_context,
    current_action,
    log_call,
    log_message,
)
from ._output import ILogger, Logger, MemoryLogger, to_file, FileDestination
from ._validation import Field, fields, MessageType, ActionType, ValidationError
from ._traceback import write_traceback, writeFailure
from ._errors import register_exception_extractor


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
    "log_message",
    "__version__",
    # Backwards compat for eliot-tree:
    "_parse",
]


from . import _version

__version__ = _version.get_versions()["version"]
