"""Module for representing Discord Snowflakes, which are unique identifiers used by Discord for various entities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from wd_discord.constants import DISCORD_EPOCH


@dataclass
class Snowflake:
    """Represents a Discord Snowflake, which is a unique identifier used by Discord for various entities."""

    _snowflake: int

    @property
    def timestamp(self) -> datetime:
        """Get the timestamp from the snowflake.

        which is the number of milliseconds since the Discord epoch (January 1, 2015).
        """
        # DISCORD_EPOCH is in milliseconds, and fromtimestamp expects seconds.
        return datetime.fromtimestamp(((self._snowflake >> 22) + DISCORD_EPOCH) / 1000, tz=UTC)

    @property
    def worker_id(self) -> int:
        """Get the worker ID from the snowflake."""
        return (self._snowflake & 0x3E0000) >> 17

    @property
    def process_id(self) -> int:
        """Get the process ID from the snowflake."""
        return (self._snowflake & 0x1F000) >> 12

    @property
    def increment(self) -> int:
        """Get the increment from the snowflake."""
        return self._snowflake & 0xFFF
