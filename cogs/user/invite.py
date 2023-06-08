
import logging

import discord
from discord import app_commands
from discord.ext import commands

import config


class Invite(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")

    @app_commands.command(
        name="bot",
        description="Invite this bot to your own server!",
        )
    async def slash_invite(self, interaction:discord.Interaction) -> None:
        self.logger.debug(f"Invite created for: id=`{interaction.user.id}`")
        await interaction.response.send_message("https://discord.com/api/oauth2/authorize?client_id=742777596734996582&permissions=4398046511095&scope=bot", ephemeral=True)

    @app_commands.command(
        name="server",
        description="get invited to the official support server"
    )
    async def slash_support(self, interaction:discord.Interaction) -> None:
        guild:discord.Guild = self.bot.get_guild(config.Main.SUPPORT_GUILD_ID)
        channel = guild.system_channel or guild.channels[0]
        invite = await channel.create_invite(max_uses=1, max_age=60, reason=f"Support command used by {interaction.user.mention}")
        await interaction.response.send_message(invite.url, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    # sourcery skip: instance-method-first-arg-name
	await bot.add_cog(Invite(bot))
