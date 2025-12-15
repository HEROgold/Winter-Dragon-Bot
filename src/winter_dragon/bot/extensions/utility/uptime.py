"""Module containing a cog for showing bot uptime."""

import datetime

import discord
from discord import app_commands

from winter_dragon.bot.core.cogs import GroupCog


class Uptime(GroupCog, auto_load=True):
    """Cog for showing the bot's uptime."""

    @app_commands.command(name="bot", description="Show bot's current uptime")
    async def slash_uptime_bot(self, interaction: discord.Interaction) -> None:
        """Send a message with the bot's current uptime."""
        await interaction.response.send_message(f"Bot uptime: {datetime.datetime.now(datetime.UTC) - self.bot.launch_time}")
