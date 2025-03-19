# TODO @HEROgold: combine with the website
# 137
from config import config
from core.bot import WinterDragon
from discord.ext.prometheus import PrometheusCog


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    if config["Main"]["log_level"] == "DEBUG":
        await bot.add_cog(PrometheusCog(bot))
