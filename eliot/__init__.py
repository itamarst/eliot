"""
Eliot: Logging as Storytelling.
"""

from ._version import __version__

# Expose the public API:
from ._message import Message
from ._action import startAction, startTask, Action
from ._output import ILogger, Logger, MemoryLogger, pretty_print
from ._validation import Field, fields, MessageType, ActionType
from ._traceback import writeTraceback, writeFailure
addDestination = Logger._destinations.add
removeDestination = Logger._destinations.remove


# PEP 8 variants:
start_action = startAction
start_task = startTask
write_traceback = writeTraceback
write_failure = writeFailure
add_destination = addDestination
remove_destination = removeDestination



__all__ = ["Message", "writeTraceback", "writeFailure",
           "startAction", "startTask", "Action",
           "Field", "fields", "MessageType", "ActionType",
           "ILogger", "Logger", "MemoryLogger", "addDestination",
           "removeDestination", "pretty_print",

           # PEP 8 variants:
           "write_traceback", "write_failure", "start_action", "start_task",
           "add_destination", "remove_destination",

           "__version__",
           ]
