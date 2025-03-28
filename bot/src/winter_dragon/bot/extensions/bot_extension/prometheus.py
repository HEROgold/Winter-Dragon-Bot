# TODO @HEROgold: combine with the website
# 137
from discord.ext.prometheus import PrometheusCog
from winter_dragon.bot.config import config
from winter_dragon.bot.core.bot import WinterDragon


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    if config.get("Main", "log_level") == "DEBUG":
        await bot.add_cog(PrometheusCog(bot))
