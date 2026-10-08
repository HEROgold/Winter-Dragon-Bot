"""Base error helpers for Discord command handling."""

from __future__ import annotations

lazy from abc import ABC, abstractmethod
lazy from datetime import UTC, datetime
lazy from typing import TYPE_CHECKING, Self

from wd_discord.embed import Embed
lazy from herogold.log import LoggerMixin
lazy from wd_discord.gateway.events import Interaction

lazy from .factory import ErrorFactory


if TYPE_CHECKING:
    from wd_bot.bot import Bot

    from wd_errors.base import BaseError

class DiscordError(ABC, LoggerMixin):
    """Base class for Error."""

    def __init_subclass__(cls: type[Self], *, error_type: type[BaseError]) -> None:
        """Register the subclass with the factory."""
        ErrorFactory.register(error_type, cls)

    def __init__(
        self,
        bot: Bot,
        interaction: Interaction,
        command_error: BaseError,
    ) -> None:
        """Initialize the Error."""
        self.timestamp = datetime.now(UTC)
        self.bot = bot
        self.interaction = interaction
        self.command_error = command_error
        self.logger.debug(
            t"Initialized {self.__class__.__name__} at {self.timestamp} for {command_error!r}",
            exc_info=command_error,
        )

    async def handle(self) -> None:
        """Handle the Error.

        If you need to handle more complex logic, override this method, and call super().handle().
        This then sends the embed created by create_embed() using send_message().
        """
        embed = self.create_embed()
        await self.send_message(embed)

    @abstractmethod
    def create_embed(self) -> Embed:
        """Create an embed for the Error."""

    async def send_message(self, response: Embed | str) -> None:
        """Send an embed response to the interaction or context."""
        match response:
            case Embed():
                await self._send_response_embed(response)
            case str():
                await self._send_response_embed(Embed(description=response))

    async def _send_response_embed(self, embed: Embed) -> None:
        if isinstance(self.interaction, Interaction):
            if self.interaction.response.is_done():
                await self.interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await self.interaction.response.send_message(embed=embed, ephemeral=True)
