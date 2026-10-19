"""The /uptime command group: how long the bot has been running."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_discord.timestamp import DiscordTime


if TYPE_CHECKING:
    lazy from datetime import datetime

    lazy from wd_discord import CommandInteraction


def uptime_message(launch_time: datetime) -> str:
    """Return the reply to /uptime bot: when the bot started, as an absolute and a relative Discord timestamp."""
    return f"Online since {DiscordTime(launch_time).with_relative()}"


class Uptime(GroupCog, name="uptime", description="Show how long the bot has been running"):
    """Cog for showing the bot's uptime."""

    @Cog.command(name="bot", description="Show the bot's current uptime")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def bot_uptime(self, interaction: CommandInteraction) -> None:
        """Reply with when the bot started."""
        await interaction.respond(uptime_message(self.bot.launch_time))
