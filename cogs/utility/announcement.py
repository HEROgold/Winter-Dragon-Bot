import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
import config
import rainbow

class Announce(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    @app_commands.command(
    name="announcement",
    description="Using this command will ping everyone and put your message in a clean embed!"
    )
    @app_commands.checks.bot_has_permissions(mention_everyone=True)
    @app_commands.checks.has_permissions(mention_everyone=True)
    async def announce(self, interaction:discord.Interaction, message:str):
        await interaction.response.defer()
        member = interaction.user
        emb = discord.Embed(title="Announcement!", description=f"{message}", colour=random.choice(rainbow.RAINBOW))
        emb.set_author(name=(member.display_name), icon_url=(member.avatar.url))
        emb.timestamp = datetime.datetime.now()
        await interaction.followup.send(embed=emb)
        if config.announcement.mention_all == True:
            mass_ping = await interaction.channel.send("<@everyone>")
            await mass_ping.delete()


async def setup(bot:commands.Bot):
	await bot.add_cog(Announce(bot))