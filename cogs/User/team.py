import discord, math, random
from discord.ext import commands

class Team(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, brief="Usage: Team (X) (name1) (name2)...", description="Use the team command to create an X number of teams and fill them evenly with all provided names or mentioned users.")
    async def team(self, ctx, amount:int, *, user_names:str):
        names = user_names.split()
        length = len(names)
        random.shuffle(names)
        divide = length // amount
        modulo = length % amount
        d = {}
        em = discord.Embed(title="Teams List!", colour=(random.randint(0,16777215)))
        print(f"modulo {modulo} , divide {divide}")
        if (math.floor(divide)) <= 0:
            await ctx.send(f"Not enough Users to fill all teams! got {length} users to fill {amount} teams.")
        else:
            for i in range(0, amount):
                d[i] = {}
                for x in range(0, math.ceil(divide)):
                    d[i][x] = names.pop()
            for i in range(0, math.ceil(modulo)):
                d[i][x+1] = names.pop()
            for k,v in d.items():
                namelist = []
                for i in v.values():
                    namelist.append(str(i))
                em.add_field(name=(f"TEAM {k+1}"), value=namelist)

            await ctx.send(embed = em)

def setup(bot):
	bot.add_cog(Team(bot))