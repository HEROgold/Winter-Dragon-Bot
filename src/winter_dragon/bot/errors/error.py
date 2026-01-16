"""Base error helpers for Discord command handling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self, overload

from discord import DiscordException, Embed, Interaction
from discord.ext.commands import Context
from herogold.log import LoggerMixin

from .factory import ErrorFactory


if TYPE_CHECKING:
    from discord.app_commands.errors import AppCommandError
    from discord.ext.commands.bot import BotBase
    from discord.ext.commands.errors import CommandError

    from winter_dragon.bot.core.bot import BotT


type ResponseTypes = Embed | str


class DiscordError(ABC, LoggerMixin):
    """Base class for Error."""

    def __init_subclass__(cls: type[Self], *, error_type: type[DiscordException]) -> None:
        """Register the subclass with the factory."""
        ErrorFactory.register(error_type, cls)

    @overload
    def __init__(self, bot: BotBase, interaction: Interaction, command_error: AppCommandError) -> None: ...
    @overload
    def __init__(self, bot: BotBase, interaction: Context[BotT], command_error: CommandError) -> None: ...

    def __init__(
        self,
        bot: BotBase,
        interaction: Context[BotT] | Interaction,
        command_error: DiscordException,
    ) -> None:
        """Initialize the Error."""
        self.timestamp = datetime.now(UTC)
        self.bot = bot
        self.interaction = interaction
        self.command_error = command_error
        self.logger.debug(
            f"Initialized {self.__class__.__name__} at {self.timestamp} for {command_error!r}", exc_info=command_error
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

    async def send_message(self, response: ResponseTypes) -> None:
        """Send an embed response to the interaction or context."""
        match response:
            case Embed():
                await self._send_response_embed(response)
            case str():
                await self._send_response_embed(Embed(description=response))
            case _:
                msg = f"Unsupported response type: {type(response).__name__}"
                raise TypeError(msg)

    async def _send_response_embed(self, embed: Embed) -> None:
        if isinstance(self.interaction, Interaction):
            if self.interaction.response.is_done():
                await self.interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await self.interaction.response.send_message(embed=embed, ephemeral=True)
        if isinstance(self.interaction, Context):
            await self.interaction.send(embed=embed)
