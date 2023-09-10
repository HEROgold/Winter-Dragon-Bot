import discord
from discord import app_commands

from tools.config_reader import config
from _types.cogs import GroupCog #, Cog
from _types.bot import WinterDragon


@app_commands.guilds(config.getint("Main", "support_guild_id"))
class TEMP(GroupCog):
    TEMP_GROUP = app_commands.Group(name="TEMPGroup", description="TEMP")

    @TEMP_GROUP.command()
    async def slash_TEMP_GROUP(self, interaction: discord.Integration) -> None:
        """TEMP"""
        raise NotImplementedError("No code!")


    @app_commands.command(name="TEMP", description="TEMP")
    async def slash_TEMP(self, interaction: discord.Interaction) -> None:
        """TEMP"""
        raise NotImplementedError("No code!")


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(TEMP(bot))
