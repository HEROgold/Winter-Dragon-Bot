"""Contains the Clash cog for the bot.

Allows for automatic event reminders for the Clash event in League of Legends.
Allows for LFG (Looking For Group) for the Clash event in League of Legends.
"""

from core.bot import WinterDragon
from discord.ext import commands


class Clash(commands.Cog):
    pass


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Clash(bot))
