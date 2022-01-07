import discord
from discord.ext import commands

class Purge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #@commands.Cog.listener()
    #EVENt LISTENER EXAPLE!

    @commands.command(aliases=("clean","delete"), pass_context=True, brief="Remove last X amount of messages", description="Purge -1 tries to remove all message in a channel. Won't work for older messages.") #Clear X ammount of message in channel
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, count:int):
        if count == -1:
            await ctx.channel.purge()
            await ctx.send("{} Killed {} Messages.".format(ctx.author.mention, count))
        else:
            await ctx.channel.purge(limit=count)
            await ctx.send("{} Killed {} Messages.".format(ctx.author.mention, count))

def setup(bot):
	bot.add_cog(Purge(bot))