"""Base error handler class for app command errors."""

from __future__ import annotations

lazy from abc import ABC
lazy from typing import override

lazy from wd_discord.embed import Embed, EmbedFooter

lazy from wd_errors.base import BaseError
lazy from wd_errors.error import DiscordError


class BaseError(DiscordError, ABC, error_type=BaseError):
    """Base error handler class for app command errors."""

    title: str = "❌ An Error Occurred"
    description: str = "An unexpected error occurred."
    footer: str = "**Please report this issue and include the timestamp:** {timestamp}"

    @property
    def timestamp_str(self) -> str:
        """Returns the timestamp of when the error occurred in HH:MM:SS.mmm format."""
        return self.timestamp.strftime("%H:%M:%S.%f")[:-3]

    @override
    def create_embed(self) -> Embed:
        return Embed(
            title=self.title,
            description=self.description,
            color=0xFF0000,
            footer = EmbedFooter(text=self.footer.format(timestamp=self.timestamp_str)),
        )
