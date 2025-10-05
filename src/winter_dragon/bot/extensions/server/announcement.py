"""A cog for announcing messages."""
import datetime
import random

import discord
from discord import app_commands
from winter_dragon.bot.config import Config
from winter_dragon.bot.tools import rainbow

from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog


class Announce(Cog):
    """A cog for announcing messages about the bot to all servers."""

    mention_all = Config(default=True)

    @app_commands.command(
            name="announcement",
            description="Using this command will ping everyone and put your message in a clean embed!")
    @app_commands.checks.has_permissions(mention_everyone=True)
    async def announce(self, interaction: discord.Interaction, message:str) -> None:
        """Send an announcement to all servers."""
        member = interaction.user
        avatar = member.avatar.url if member.avatar else member.default_avatar.url
        emb = discord.Embed(title="Announcement!", description=f"{message}", color=random.choice(rainbow.RAINBOW))  # noqa: S311
        emb.set_author(name=(member.display_name), icon_url=avatar)
        emb.timestamp = datetime.datetime.now()  # noqa: DTZ005
        await interaction.response.send_message(embed=emb)
        if self.mention_all:
            mass_ping = await interaction.channel.send("<@everyone>") # type: ignore[reportAttributeAccessIssue]
            await mass_ping.delete()


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(Announce(bot=bot))
