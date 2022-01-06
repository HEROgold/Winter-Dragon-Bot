import discord
from discord.ext import commands
from discord.errors import Forbidden

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #@commands.Cog.listener()
    #EVENt LISTENER EXAPLE!

    @commands.command()
    async def Help(self, ctx):
        dm = await ctx.author.create_dm()
        await dm.send("")

    async def send_embed(ctx, embed):
        try:
            await ctx.send(embed=embed)
        except:
            try:
                await ctx.send("I can't send embeds. Please check permissions")
            except:
                await dm.send(f"I can't send any message in {ctx.channel.name} on {ctx.guild.name}\n inform the server team about this issue.", embed=embed)
def setup(bot):
	bot.add_cog(Help(bot))