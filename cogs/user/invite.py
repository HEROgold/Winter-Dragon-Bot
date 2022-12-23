import discord
from discord.ext import commands
from config import invite as config

class Invite(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    @commands.command(brief="Invite this bot to your own server!",
                    description="Using this command will put the link to invite this bot chat.",
                    usage="`invite`")
    @commands.has_permissions()
    async def invite(self, ctx:commands.Context):
        if config.dm_user == False:
            await ctx.send("https://discord.com/api/oauth2/authorize?client_id=742777596734996582&permissions=8&scope=bot")
        elif config.dm_user == True:
            dm = await ctx.author.create_dm()
            await dm.send("https://discord.com/api/oauth2/authorize?client_id=742777596734996582&permissions=8&scope=bot")

async def setup(bot:commands.Bot):
	await bot.add_cog(Invite(bot))