import discord
from discord import app_commands

from _types.bot import WinterDragon
from _types.cogs import GroupCog  #, Cog
from tools.config_reader import config


@app_commands.guilds(config.getint("Main", "support_guild_id"))
class TEMP(GroupCog):
    TEMP_GROUP = app_commands.Group(name="TEMPGroup", description="TEMP")

    @TEMP_GROUP.command() # type: ignore
    async def slash_TEMP_GROUP(self, interaction: discord.Integration) -> None:
        """TEMP"""
        raise NotImplementedError("No code!")


    @app_commands.command(name="TEMP", description="TEMP")
    async def slash_TEMP(self, interaction: discord.Interaction) -> None:
        """TEMP"""
        raise NotImplementedError("No code!")


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(TEMP(bot))
