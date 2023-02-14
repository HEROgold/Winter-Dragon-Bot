import logging

import discord
from discord import app_commands
from discord.ext import commands

import config

class Invite(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(f"winter_dragon.{self.__class__.__name__}")
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__

    @app_commands.command(
        name="invite",
        description="Invite this bot to your own server!",
        )
    async def slash_invite(self, interaction:discord.Interaction):
        self.logger.debug(f"Invite created for: id=`{interaction.user.id}`")
        await interaction.response.send_message("https://discord.com/api/oauth2/authorize?client_id=742777596734996582&permissions=4398046511095&scope=bot", ephemeral=True)

    @app_commands.command(
        name="support",
        description="get invited to the official support server"
    )
    async def slash_support(self, interaction:discord.Interaction):
        guild:discord.Guild = self.bot.get_guild(config.Main.SUPPORT_GUILD_ID)
        channel = guild.system_channel or guild.channels[0]
        invite = await channel.create_invite(max_uses=1, max_age=60, reason=f"Support command used by {interaction.user.mention}")
        await interaction.response.send_message(invite.url, ephemeral=True)

async def setup(bot:commands.Bot):
    # sourcery skip: instance-method-first-arg-name
	await bot.add_cog(Invite(bot))
