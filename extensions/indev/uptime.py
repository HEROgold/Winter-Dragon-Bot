import datetime
import logging

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands

from tools.config_reader import config


class Uptime(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")


    @app_commands.command(name="bot", description="Show bot's current uptime")
    async def slash_uptime_bot(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"Bot uptime: {datetime.datetime.now(datetime.timezone.utc) - self.bot.launch_time}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Uptime(bot))