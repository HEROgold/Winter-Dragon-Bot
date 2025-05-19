"""."""

from discord.ext.prometheus import PrometheusCog
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.settings import Settings


# TODO @HEROgold: combine with the website
# 137

async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    if Settings.log_level == "DEBUG":
        await bot.add_cog(PrometheusCog(bot))
