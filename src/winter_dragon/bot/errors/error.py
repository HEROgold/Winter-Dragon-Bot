"""Base error helpers for Discord command handling."""

from abc import ABC, abstractmethod
from typing import Self, overload

from discord import Embed, Interaction
from discord.app_commands.errors import AppCommandError
from discord.ext.commands import Context
from discord.ext.commands.bot import BotBase
from discord.ext.commands.errors import CommandError
from herogold.log import LoggerMixin

from winter_dragon.bot.core.bot import BotT

from .alias import DiscordCommandError
from .factory import ErrorFactory


class DiscordError(ABC, LoggerMixin):
    """Base class for Error."""

    @overload
    def __init__(self, bot: BotBase, interaction: Interaction, command_error: AppCommandError) -> None: ...
    @overload
    def __init__(self, bot: BotBase, interaction: Context[BotT], command_error: CommandError) -> None: ...

    def __init__(
        self,
        bot: BotBase,
        interaction: Context[BotT] | Interaction,
        command_error: DiscordCommandError,
    ) -> None:
        """Initialize the Error."""
        super().__init__()
        self.bot = bot
        self.interaction = interaction
        self.command_error = command_error

    @abstractmethod
    async def handle(self) -> None:
        """Handle the Error."""

    @abstractmethod
    def create_embed(self) -> Embed:
        """Create an embed for the Error."""

    def __init_subclass__(cls: type[Self], error_type: DiscordCommandError) -> None:
        """Register the subclass with the factory."""
        ErrorFactory.register(error_type, cls)
