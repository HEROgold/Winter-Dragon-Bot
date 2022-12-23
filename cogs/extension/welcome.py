import logging
import discord
from discord.ext import commands
from config import welcome as config

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot
    
    @commands.Cog.listener() # Welcome a user if they join!
    async def on_member_join(self, member:discord.Member):
        channel = member.guild.system_channel
        if channel is not None and config.dm_user == False:
            await channel.send(f"Welcome {member.mention} to {member.guild}")
        elif channel is not None and config.dm_user == True:
            dm = await member.create_dm()
            dm.send(f"Welcome {member.mention} to {member.guild}")
        else:
            logging.warning("No system_channel to welcome user to, and dm is disabled.")


async def setup(bot:commands.Bot):
	await bot.add_cog(Welcome(bot))