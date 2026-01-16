"""Handler for CommandInvokeError - catches unhandled exceptions in commands."""

from typing import override

from discord import Embed
from discord.app_commands.errors import CommandInvokeError

from winter_dragon.bot.errors.error import DiscordError


class AppCommandInvokeError(DiscordError, error_type=CommandInvokeError):
    """Handler for CommandInvokeError - catches all unhandled exceptions in app commands."""

    @override
    def create_embed(self) -> Embed:
        timestamp_str = self.timestamp.strftime("%H:%M:%S.%f")[:-3]

        embed = Embed(
            title="❌ An Error Occurred",
            description="An unexpected error occurred while executing this command.\n\n",
            color=0xFF0000,
        )
        embed.set_footer(text=f"**Please report this issue and include the timestamp:**\n{timestamp_str}")

        return embed
