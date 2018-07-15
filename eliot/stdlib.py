"""Integration with the standard library ``logging`` package."""

from logging import Handler
from ._message import Message


class EliotHandler(Handler):
    """A C{logging.Handler} that routes log messages to Eliot."""

    def emit(self, record):
        Message.log(
            message_type="eliot:stdlib",
            log_level=record.levelname,
            logger=record.name,
            message=record.getMessage()
        )


__all__ = ["EliotHandler"]
