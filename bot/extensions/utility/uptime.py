import datetime

import discord  # type: ignore
from discord import app_commands

from bot import WinterDragon
from bot.types.cogs import GroupCog


class Uptime(GroupCog):
    @app_commands.command(name="bot", description="Show bot's current uptime")
    async def slash_uptime_bot(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"Bot uptime: {datetime.datetime.now(datetime.UTC) - self.bot.launch_time}")


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Uptime(bot))
