import logging

import discord
from discord.ext import commands

import config


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot
        self.logger = logging.getLogger("winter_dragon.welcome")

    
    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member):
        channel = member.guild.system_channel
        if channel is not None and config.welcome.dm_user == False:
            await channel.send(f"Welcome {member.mention} to {member.guild}")
        elif channel is not None and config.welcome.dm_user == True and member.bot == False:
            dm = await member.create_dm()
            dm.send(f"Welcome {member.mention} to {member.guild}")
        else:
            self.logger.warning("No system_channel to welcome user to, and dm is disabled.")

async def setup(bot:commands.Bot):
	await bot.add_cog(Welcome(bot))