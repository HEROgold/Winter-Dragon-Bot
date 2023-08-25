import logging

import discord
from discord import app_commands
from discord.ext import commands

from tools.config_reader import config


@app_commands.guilds(config.getint("Main", "support_guild_id"))
class TEMP(commands.GroupCog):
    bot: commands.Bot
    logger: logging.Logger

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")


    # TEMP_GROUP = app_commands.Group(name="TEMPGroup", description="TEMP")
    # @TEMP_GROUP.command()


    @app_commands.command(name="TEMP", description="TEMP")
    async def slash_TEMP(self, interaction: discord.Interaction) -> None:
        """TEMP"""
        raise NotImplementedError("No code!")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TEMP(bot))
