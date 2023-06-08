import logging

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands

import config


@app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
class TEMP(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")

    # TEMP_GROUP = app_commands.Group(name="TEMPGroup", description="TEMP")
    # @TEMP_GROUP.command()

    @app_commands.command(name="TEMP", description="TEMP")
    async def slash_TEMP(self, interaction: discord.Interaction) -> None:
        """TEMP"""
        raise NotImplementedError("No code!")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TEMP(bot))  # type: ignore
