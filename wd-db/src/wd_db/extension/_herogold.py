"""herogold's ORM ``BaseModel``, imported without herogold writing a ``db_config.ini`` of its own.

Importing herogold's models builds its own engine from its ``DbConfig``, which by default writes its defaults to
``db_config.ini`` in the working directory. That engine and session go unused (lifecycle operations take the caller's
session), so its file is made optional here, as ``wd_config.Config.bind(optional=True)`` does for the bot's own files.
"""

lazy from pathlib import Path

from herogold.orm.core.config import DbConfig
from wd_config.config import OptionalFileWatcher


HEROGOLD_CONFIG_FILE = Path("db_config.ini")

DbConfig.write_on_edit = False
DbConfig._watcher = OptionalFileWatcher(HEROGOLD_CONFIG_FILE)  # noqa: SLF001 - confkit has no public way to swap the watcher

from herogold.orm.core.model import BaseModel  # noqa: E402 - only once DbConfig won't write


__all__ = ["BaseModel"]
