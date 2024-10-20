# TODO: combine with the website
from discord.ext.prometheus import PrometheusCog

from bot import WinterDragon
from bot.config import config


async def setup(bot: WinterDragon) -> None:
    if config["Main"]["log_level"] == "DEBUG":
        await bot.add_cog(PrometheusCog(bot))
