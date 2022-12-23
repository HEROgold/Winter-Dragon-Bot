import discord
import random
from discord.ext import commands


class love(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    @commands.cooldown(1, 1, commands.BucketType.user)
    @commands.command(
        name="love",
        brief="Find out your compatability with another person!",
        description="Use this command to find out if another person is compatible with you and your love",
        usage="`love [user]`:\n Example: `love @user1`",
    )
    async def love(self, ctx: commands.Context, *, content):
        ind = 1 if ctx.message.mentions[0] == "<@742777596734996582>" else 0
        emb = discord.Embed(
            title="Love Meter",
            description="calculating your compatibility, this process took me some time, and i finally have an answer",
            colour=0xFF0000,
        )
        for mention in ctx.message.mentions:
            random.seed((ind + ctx.message.author.id))
            emb.add_field(
                name=f"{ctx.message.mentions[ind].display_name}",
                value=f"Your compatibility with {ctx.message.mentions[ind].display_name} is {random.randint(0,100)}%",
                inline=True,
            )
            ind += 1
        await ctx.send(embed=emb)


async def setup(bot: commands.Bot):
    await bot.add_cog(love(bot))