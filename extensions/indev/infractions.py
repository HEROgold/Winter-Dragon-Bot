import discord
from discord import app_commands

from tools.config_reader import config
from _types.cogs import GroupCog #, Cog
from _types.bot import WinterDragon


@app_commands.guilds(config.getint("Main", "support_guild_id"))
class Infractions(GroupCog):
    """
    Track automod interaction from discord, keep track of amount of violations
    (Infractions)Ban users when X amount have reached. (Per guild configurable)

    TODO: Add automod rules to keep track of,
    TODO: On automod trigger, add infraction (Delete old ones)
    """


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Infractions(bot))