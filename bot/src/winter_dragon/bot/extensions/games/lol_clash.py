"""Contains the Clash cog for the bot.

Allows for automatic event reminders for the Clash event in League of Legends.
Allows for LFG (Looking For Group) for the Clash event in League of Legends.
"""

from discord.ext import commands
from winter_dragon.bot.core.bot import WinterDragon


class Clash(commands.Cog):
    """Clash cog for League of Legends."""


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(Clash(bot=bot))
