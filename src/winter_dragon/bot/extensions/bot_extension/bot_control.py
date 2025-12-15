"""Module that contains interfaces to control the bot using discord."""

from typing import Unpack

import discord
from discord import Guild, app_commands
from discord.ext import commands

from winter_dragon.bot.core.cogs import BotArgs, GroupCog
from winter_dragon.bot.core.settings import Settings


@app_commands.guilds(Settings.support_guild_id)
class BotControl(GroupCog, auto_load=True):
    """Cog to control the bot."""

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the bot control cog."""
        super().__init__(**kwargs)

    @commands.is_owner()
    @app_commands.guild_only()
    @app_commands.command(name="announce", description="Announce important messages on all servers the bot runs on")
    async def slash_bot_announce(self, interaction: discord.Interaction, msg: str) -> None:
        """Announce a message to all servers the bot is in and allowed to."""
        for guild in self.bot.guilds:
            await self._send_announcement(msg, guild)

        await interaction.response.send_message(
            "Message send to all update channels on all servers!",
            ephemeral=True,
        )

    async def _send_announcement(self, msg: str, guild: Guild) -> None:
        if guild.public_updates_channel is None:
            self.logger.warning(f"Guild {guild.name} does not have a public updates channel")
            return
        await guild.public_updates_channel.send(msg)
