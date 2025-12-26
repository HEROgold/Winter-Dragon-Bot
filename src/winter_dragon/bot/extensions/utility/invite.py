"""Module containing the invite cog for the bot."""

import discord
from discord import app_commands

from winter_dragon.bot.core.settings import Settings
from winter_dragon.discord.cogs import GroupCog


class Invite(GroupCog, auto_load=True):
    """Cog for inviting the bot to a guild or getting support."""

    @app_commands.command(name="bot", description="Invite this bot to your own guild!")
    async def slash_invite(self, interaction: discord.Interaction) -> None:
        """Send a message with the bot's invite link."""
        self.logger.debug(f"Invite created for: {interaction.user.id=}")
        await interaction.response.send_message(
            self.bot.get_bot_invite(),
            ephemeral=True,
        )

    @app_commands.command(name="guild", description="get invited to the official support guild")
    async def slash_support(self, interaction: discord.Interaction) -> None:
        """Send a message with the bot's support guild invite link."""
        guild = self.bot.get_guild(Settings.support_guild_id) or await self.bot.fetch_guild(Settings.support_guild_id)
        channel = guild.system_channel or guild.channels[0]
        invite = await channel.create_invite(
            max_uses=1,
            max_age=60,
            reason=f"Support command used by {interaction.user.mention}",
        )
        await interaction.response.send_message(invite.url, ephemeral=True)
