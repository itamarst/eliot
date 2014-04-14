"""
Eliot: An Opinionated Logging Library

    Suppose we turn from outside estimates of a man, to wonder, with keener
    interest, what is the report of his own consciousness about his doings or
    capacity: with what hindrances he is carrying on his daily labors; what
    fading of hopes, or what deeper fixity of self-delusion the years are
    marking off within him; and with what spirit he wrestles against universal
    pressure, which will one day be too heavy for him, and bring his heart to
    its final pause.

        -- George Eliot, "Middlemarch"

See http://wiki.hybrid-cluster.com/index.php?title=Logging_Design_Document for
motivation.
"""

# Expose the public API:
from ._message import Message
from ._action import startAction, startTask, Action
from ._output import ILogger, Logger, MemoryLogger
from ._validation import Field, MessageType, ActionType
from ._traceback import writeTraceback, writeFailure
addDestination = Logger._destinations.add
removeDestination = Logger._destinations.remove


__all__ = ["Message", "writeTraceback", "writeFailure",
           "startAction", "startTask", "Action",
           "Field", "MessageType", "ActionType",
           "ILogger", "Logger", "MemoryLogger", "addDestination",
           "removeDestination",
           ]
