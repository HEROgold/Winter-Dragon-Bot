"""."""

import logging

from discord.ext.prometheus import PrometheusCog
from winter_dragon.bot.settings import Settings

from winter_dragon.bot.core.bot import WinterDragon


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    if Settings.log_level == logging.DEBUG:
        await bot.add_cog(PrometheusCog(bot=bot))
