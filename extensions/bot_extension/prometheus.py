
from discord.ext.prometheus import PrometheusCog
from _types.bot import WinterDragon
from tools.config_reader import config


async def setup(bot: WinterDragon) -> None:
    if config["Main"]["log_level"] == "DEBUG":
        await bot.add_cog(PrometheusCog(bot))
