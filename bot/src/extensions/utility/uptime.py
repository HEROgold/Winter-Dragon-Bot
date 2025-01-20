import datetime

import discord
from core.bot import WinterDragon
from core.cogs import GroupCog
from discord import app_commands


class Uptime(GroupCog):
    @app_commands.command(name="bot", description="Show bot's current uptime")
    async def slash_uptime_bot(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"Bot uptime: {datetime.datetime.now(datetime.UTC) - self.bot.launch_time}")


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Uptime(bot))
