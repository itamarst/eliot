"""Integration with the standard library ``logging`` package."""

from logging import Handler

from ._message import Message
from ._traceback import write_traceback


class EliotHandler(Handler):
    """A C{logging.Handler} that routes log messages to Eliot."""

    def emit(self, record):
        Message.log(
            message_type="eliot:stdlib",
            log_level=record.levelname,
            logger=record.name,
            message=record.getMessage(),
        )
        if record.exc_info:
            write_traceback(exc_info=record.exc_info)


__all__ = ["EliotHandler"]
