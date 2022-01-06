import discord
from discord.ext import commands

class Purge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #@commands.Cog.listener()
    #EVENt LISTENER EXAPLE!

    @commands.command(aliases=("clean","delete"), pass_context=True) #Clear X ammount of message in channel
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, count):
        if count == -1:
            await ctx.channel.purge()
            confirm = await ctx.send("{} Killed {} Messages.".format(ctx.author.mention, count))
        else:
            await ctx.channel.purge(limit=count)
            confirm = await ctx.send("{} Killed {} Messages.".format(ctx.author.mention, count))

def setup(bot):
	bot.add_cog(Purge(bot))