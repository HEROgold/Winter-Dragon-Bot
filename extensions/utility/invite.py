import discord
from discord import app_commands

from _types.bot import WinterDragon
from _types.cogs import GroupCog
from tools.config_reader import config


PERMISSIONS = 70368744177655 # All permissions


class Invite(GroupCog):
    @app_commands.command(name="bot", description="Invite this bot to your own server!")
    async def slash_invite(self, interaction: discord.Interaction) -> None:
        self.logger.debug(f"Invite created for: {interaction.user.id=}")
        await interaction.response.send_message(
            f"https://discord.com/oauth2/authorize?client_id={self.bot.application_id}&permissions={PERMISSIONS}&scope=bot",
            ephemeral=True,
        )


    @app_commands.command(name="server", description="get invited to the official support server")
    async def slash_support(self, interaction: discord.Interaction) -> None:
        guild = self.bot.get_guild(config.getint("Main", "support_guild_id")) or \
            await self.bot.fetch_guild(config.getint("Main", "support_guild_id"))
        channel = guild.system_channel or guild.channels[0]
        invite = await channel.create_invite(max_uses=1, max_age=60, reason=f"Support command used by {interaction.user.mention}")
        await interaction.response.send_message(invite.url, ephemeral=True)


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Invite(bot))
