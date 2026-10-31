"""Module-level loggers that reach a log file.

``herogold.log.setup()`` only gives a logger its own ``logs/<name>.log`` when it belongs to a ``LoggerMixin`` class.
:func:`get_logger` gives each name such a logger, so a module-level logger gets a file like a class does.
"""

from __future__ import annotations

lazy from functools import cache
lazy from typing import TYPE_CHECKING

lazy from herogold.log import LoggerMixin


if TYPE_CHECKING:
    from herogold.log import Logger


@cache
def get_logger(name: str) -> Logger:
    """Return the logger for ``name``, the same one on every call, writing to ``logs/wd.<name>.log``."""
    owner = type(name, (LoggerMixin,), {"__module__": "wd"})
    return owner().logger
