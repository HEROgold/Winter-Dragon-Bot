# TODO @HEROgold: combine with the website
# 137
from discord.ext.prometheus import PrometheusCog

from bot.core import WinterDragon
from bot.config import config


async def setup(bot: WinterDragon) -> None:
    if config["Main"]["log_level"] == "DEBUG":
        await bot.add_cog(PrometheusCog(bot))
