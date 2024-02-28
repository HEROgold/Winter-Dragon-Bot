import datetime
import random

import discord
from discord import app_commands

from _types.bot import WinterDragon
from _types.cogs import Cog
from tools import rainbow
from tools.config_reader import config


class Announce(Cog):
    @app_commands.command(name="announcement", description="Using this command will ping everyone and put your message in a clean embed!")
    @app_commands.checks.has_permissions(mention_everyone=True)
    async def announce(self, interaction:discord.Interaction, message:str) -> None:
        member = interaction.user
        emb = discord.Embed(title="Announcement!", description=f"{message}", color=random.choice(rainbow.RAINBOW))
        emb.set_author(name=(member.display_name), icon_url=(member.avatar.url))
        emb.timestamp = datetime.datetime.now()  # noqa: DTZ005
        await interaction.response.send_message(embed=emb)
        if config.getboolean("Announcement", "MENTION_ALL"):
            mass_ping = await interaction.channel.send("<@everyone>")
            await mass_ping.delete()


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Announce(bot))
