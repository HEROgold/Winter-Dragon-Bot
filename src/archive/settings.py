"""The archive's settings, in their own ``archive.ini``; its token lives with the bot's in ``bot.ini``."""

from wd_config import Config
from wd_config.constants import ARCHIVE_CONFIG_FILE
from wd_discord.intents import Intents


class ArchiveConfig[T](Config[T]):
    """Config descriptor scoped to the archive settings file."""


ArchiveConfig.bind(ARCHIVE_CONFIG_FILE)


class ArchiveSettings:
    """How the archive connects and writes."""

    intents = ArchiveConfig(int(Intents.all()))
    """Gateway intents as an int; every intent by default, privileged ones included."""
    batch_size = ArchiveConfig(200)
    """Most events written per database transaction."""
    batch_interval = ArchiveConfig(0.5)
    """Seconds a batch waits to fill up before it is written anyway."""
    queue_limit = ArchiveConfig(50_000)
    """Events held while the database is slow or down; beyond it new events are dropped (the log file keeps them)."""
    raw_event_retention_days = ArchiveConfig(30)
    """Days raw events are kept before the daily purge deletes them."""
