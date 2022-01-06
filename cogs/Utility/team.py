import discord
from discord.ext import commands

import discord, random

class Team(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #@commands.Cog.listener()
    #EVENt LISTENER EXAPLE!

    @commands.command(pass_context=True) #Clear X ammount of message in channel
    async def team(self, ctx, *, ctxcont:str):
        words = ctxcont.split()
        random.shuffle(words)
        lenght = len(words)
        splitwords = lenght//2
        listA = words[:splitwords]
        listB = words[splitwords:]
        print(listA)
        em = discord.Embed()
        em.add_field(name="TEAM A", value=listA)
        em.add_field(name="TEAM B", value=listB)
        await ctx.send(embed = em)

def setup(bot):
	bot.add_cog(Team(bot))
