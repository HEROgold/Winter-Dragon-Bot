import discord
from discord.ext import commands
from config import welcome as config

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener() # Welcome a user if they join!
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel is not None and config.dm_user == False:
            await channel.send(f"Welcome {member.mention} to {ctx.guild}")
        elif config.dm_user == True:
            dm = await ctx.message.author.create_dm()
            dm.send(f"Welcome {member.mention} to {ctx.guild}")
        else:
            print(f"No system_channel to welcome user to, and dm is disabled.")


def setup(bot):
	bot.add_cog(Welcome(bot))