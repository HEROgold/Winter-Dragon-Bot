"""Handler for CommandNotFound - catches unhandled exceptions in commands."""

from datetime import UTC, datetime
from typing import override

from discord import Embed
from discord.app_commands.errors import CommandNotFound

from winter_dragon.bot.errors.error import DiscordError


class CommandNotFoundError(DiscordError, error_type=CommandNotFound):
    """Handler for CommandNotFound - catches all unhandled exceptions in app commands."""

    @override
    def create_embed(self) -> Embed:
        error_time = datetime.now(UTC)
        timestamp_str = error_time.strftime("%H:%M:%S.%f")[:-3]

        embed = Embed(
            title="❌ Command Not Found",
            description="The command you tried to use was not found.",
            color=0xFF0000,
            timestamp=error_time,
        )
        embed.set_footer(text=f"**Please report this issue and include the timestamp:**\n`{timestamp_str}`")

        return embed
