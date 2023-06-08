import datetime
import random

import discord
from discord import app_commands
from discord.ext import commands

import config
import rainbow


class Announce(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
    name="announcement",
    description="Using this command will ping everyone and put your message in a clean embed!"
    )
    @app_commands.checks.has_permissions(mention_everyone=True)
    async def announce(self, interaction:discord.Interaction, message:str) -> None:
        member = interaction.user
        emb = discord.Embed(title="Announcement!", description=f"{message}", color=random.choice(rainbow.RAINBOW))
        emb.set_author(name=(member.display_name), icon_url=(member.avatar.url))
        emb.timestamp = datetime.datetime.now()
        await interaction.response.send_message(embed=emb)
        if config.Announcement.MENTION_ALL == True:
            mass_ping = await interaction.channel.send("<@everyone>")
            await mass_ping.delete()


async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Announce(bot))