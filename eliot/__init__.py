"""
Eliot: Logging for Complex & Distributed Systems.
"""
from warnings import warn

# Expose the public API:
from ._message import Message
from ._action import (
    startAction, startTask, Action, preserve_context, current_action,
    use_asyncio_context,
)
from ._output import (
    ILogger,
    Logger,
    MemoryLogger,
    to_file,
    FileDestination,
)
from ._validation import Field, fields, MessageType, ActionType
from ._traceback import writeTraceback, writeFailure
from ._errors import register_exception_extractor
from ._version import get_versions


# Backwards compatibility:
def add_destination(destination):
    warn(
        "add_destination is deprecated since 1.1.0. "
        "Use add_destinations instead.",
        DeprecationWarning,
        stacklevel=2
    )
    Logger._destinations.add(destination)


# Backwards compatibilty:
addDestination = add_destination
removeDestination = Logger._destinations.remove
addGlobalFields = Logger._destinations.addGlobalFields

# PEP 8 variants:
start_action = startAction
start_task = startTask
write_traceback = writeTraceback
write_failure = writeFailure
add_destinations = Logger._destinations.add
remove_destination = removeDestination
add_global_fields = addGlobalFields


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
    "__version__",
]

__version__ = get_versions()['version']
del get_versions
