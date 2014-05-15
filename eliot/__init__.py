"""
Eliot: Logging as Storytelling.
"""

from ._version import __version__

# Expose the public API:
from ._message import Message
from ._action import startAction, startTask, Action
from ._output import ILogger, Logger, MemoryLogger
from ._validation import Field, fields, MessageType, ActionType
from ._traceback import writeTraceback, writeFailure
addDestination = Logger._destinations.add
removeDestination = Logger._destinations.remove


__all__ = ["Message", "writeTraceback", "writeFailure",
           "startAction", "startTask", "Action",
           "Field", "fields", "MessageType", "ActionType",
           "ILogger", "Logger", "MemoryLogger", "addDestination",
           "removeDestination",

           "__version__",
           ]
