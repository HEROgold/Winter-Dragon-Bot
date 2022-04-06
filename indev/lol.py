import discord
from discord.ext import commands
import cassiopeia as cass
import config

class lol(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        cass.set_riot_api_key(config.lol.key)

    #@commands.Cog.listener()
    #EVENt LISTENER EXAPLE!

    @commands.command(brief="WIP", description="WIP")
    async def lol(self, ctx):
        print("HI")

def setup(bot):
	bot.add_cog(lol(bot))