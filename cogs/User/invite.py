import discord
from discord.ext import commands

class Invite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #@commands.Cog.listener()
    #EVENt LISTENER EXAPLE!

    @commands.command() #Send bot invite link to chat!
    @commands.has_permissions(manage_guild=True)
    async def invite(self, ctx):
        await ctx.send("https://discord.com/api/oauth2/authorize?client_id=742777596734996582&permissions=8&scope=bot")

def setup(bot):
	bot.add_cog(Invite(bot))