"""Module for representing Discord Snowflakes, which are unique identifiers used by Discord for various entities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic_core import core_schema

from wd_discord.constants import DISCORD_EPOCH


if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler
    from pydantic_core import CoreSchema


@dataclass
class Snowflake:
    """Represents a Discord Snowflake, which is a unique identifier used by Discord for various entities."""

    _snowflake: int

    @classmethod
    def _validate(cls, value: Any) -> Snowflake:  # noqa: ANN401 - pydantic hands us an untyped input
        """Coerce an ``int`` or decimal ``str`` (Discord's wire form) into a :class:`Snowflake`."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            value = int(value)
        if isinstance(value, int):
            return cls(value)
        msg = f"Cannot build Snowflake from {type(value).__name__}."
        raise TypeError(msg)

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: GetCoreSchemaHandler) -> CoreSchema:
        """Validate from ``int``/``str`` and serialise back to Discord's decimal-string form."""
        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda snowflake: str(snowflake._snowflake),  # noqa: SLF001 - own attribute
                return_schema=core_schema.str_schema(),
                when_used="json",
            ),
        )

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
