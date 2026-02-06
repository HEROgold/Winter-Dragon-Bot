"""Base error handler class for app command errors."""

from abc import ABC
from typing import Self, override

from discord import DiscordException, Embed

from winter_dragon.bot.errors.error import DiscordError


class BaseError(DiscordError, ABC, error_type=DiscordException):
    """Base error handler class for app command errors."""

    title: str = "❌ An Error Occurred"
    description: str = "An unexpected error occurred."
    footer: str = "**Please report this issue and include the timestamp:** {timestamp}"

    def __init_subclass__(cls: type[Self], *, error_type: type[DiscordException]) -> None:
        """Register the subclass with the factory."""
        super().__init_subclass__(error_type=error_type)

    @property
    def timestamp_str(self) -> str:
        """Returns the timestamp of when the error occurred in HH:MM:SS.mmm format."""
        return self.timestamp.strftime("%H:%M:%S.%f")[:-3]

    @override
    def create_embed(self) -> Embed:
        embed = Embed(
            title=self.title,
            description=self.description,
            color=0xFF0000,
        )
        embed.set_footer(text=self.footer.format(timestamp=self.timestamp_str))

        return embed
