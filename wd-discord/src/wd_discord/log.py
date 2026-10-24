"""Module-level loggers that reach a log file.

herogold's ``getLogger`` returns a new logger on every call, outside ``logging``'s hierarchy and without handlers
(HeroPy#55), so a module-level ``logger = getLogger("name")`` never writes to ``logs/``: its records only reach stderr
through ``logging.lastResort``. :func:`get_logger` instead gives each name the logger herogold sets up for a
``LoggerMixin`` class, which writes ``logs/<name>.log`` and the console. Once HeroPy#55 is fixed, the call sites go
back to ``herogold.log.getLogger`` and this module goes.
"""

from __future__ import annotations

lazy from functools import cache
lazy from typing import TYPE_CHECKING

lazy from herogold.log import LoggerMixin


if TYPE_CHECKING:
    from herogold.log import Logger


# TODO(Herogold, HeroPy#55): use herogold.log.getLogger once it returns registered loggers.  # noqa: FIX002


@cache
def get_logger(name: str) -> Logger:
    """Return the logger for ``name``, the same one on every call, writing to ``logs/<name>.log``."""
    owner = type(name, (LoggerMixin,), {"__module__": "wd"})
    return owner().logger
