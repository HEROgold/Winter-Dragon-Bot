"""Discord timestamp markup: ``<t:EPOCH:STYLE>``, shown in each reader's own timezone and locale.

See https://docs.discord.com/developers/reference#message-formatting-timestamp-styles
"""

from __future__ import annotations

from dataclasses import dataclass
lazy from enum import StrEnum
lazy from typing import TYPE_CHECKING, override


if TYPE_CHECKING:
    lazy from datetime import datetime


class TimestampStyle(StrEnum):
    """How Discord renders a timestamp; the examples are for 2021-04-20 16:20:30 in an en-GB client."""

    SHORT_TIME = "t"
    """16:20"""
    MEDIUM_TIME = "T"
    """16:20:30"""
    SHORT_DATE = "d"
    """20/04/2021"""
    LONG_DATE = "D"
    """20 April 2021"""
    LONG_DATE_SHORT_TIME = "f"
    """20 April 2021 at 16:20 (Discord's default)"""
    FULL_DATE_SHORT_TIME = "F"
    """Tuesday, 20 April 2021 at 16:20"""
    SHORT_DATE_SHORT_TIME = "s"
    """20/04/2021, 16:20"""
    SHORT_DATE_MEDIUM_TIME = "S"
    """20/04/2021, 16:20:30"""
    RELATIVE_TIME = "R"
    """4 years ago"""


@dataclass(frozen=True)
class DiscordTime:
    """A moment, rendered as Discord timestamp markup.

    ``str(time)`` gives Discord's default style; ``f"{time:R}"`` takes a :class:`TimestampStyle` letter.
    """

    moment: datetime

    @property
    def epoch(self) -> int:
        """The moment in whole seconds since the Unix epoch, as Discord expects."""
        return int(self.moment.timestamp())

    def format(self, style: TimestampStyle | None = None) -> str:
        """Return the markup for this moment in ``style``, or in Discord's default style when not given."""
        return f"<t:{self.epoch}>" if style is None else f"<t:{self.epoch}:{style}>"

    def with_relative(self, style: TimestampStyle = TimestampStyle.FULL_DATE_SHORT_TIME) -> str:
        """Return this moment in ``style``, followed by how long ago or from now it is: ``<t:E:F> (<t:E:R>)``."""
        return f"{self.format(style)} ({self.format(TimestampStyle.RELATIVE_TIME)})"

    @override
    def __str__(self) -> str:
        return self.format()

    @override
    def __format__(self, format_spec: str) -> str:
        return self.format(TimestampStyle(format_spec) if format_spec else None)
