"""
Eliot: Logging for Complex & Distributed Systems.
"""
# Expose the public API:
from ._message import Message
from ._action import startAction, startTask, Action
from ._output import (
    ILogger, Logger, MemoryLogger, to_file, FileDestination,
)
from ._validation import Field, fields, MessageType, ActionType
from ._traceback import writeTraceback, writeFailure
addDestination = Logger._destinations.add
removeDestination = Logger._destinations.remove
addGlobalFields = Logger._destinations.addGlobalFields

# PEP 8 variants:
start_action = startAction
start_task = startTask
write_traceback = writeTraceback
write_failure = writeFailure
add_destination = addDestination
remove_destination = removeDestination
add_global_fields = addGlobalFields


__all__ = ["Message", "writeTraceback", "writeFailure",
           "startAction", "startTask", "Action",
           "Field", "fields", "MessageType", "ActionType",
           "ILogger", "Logger", "MemoryLogger", "addDestination",
           "removeDestination", "addGlobalFields", "FileDestination",

           # PEP 8 variants:
           "write_traceback", "write_failure", "start_action", "start_task",
           "add_destination", "remove_destination", "add_global_fields",
           "to_file",

           "__version__",
           ]

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
