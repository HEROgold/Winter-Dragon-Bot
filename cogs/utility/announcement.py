import discord
from discord.ext import commands
import random
import datetime
from config import announcement as config

class Announce(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    @commands.has_permissions(mention_everyone=True) # send nice embed message to create an announcement
    @commands.command(aliases=("announcement", "announcey"),
    pass_context=True, brief="Create an announcement in the current channel, mention everyone.",
    description="Using this command will ping everyone and put your message in a clean embed!"
    )
    async def announce(self, ctx:commands.Context, *, message):
        member = ctx.author
        emb = discord.Embed(title="Announcement!", description=f"{message}", colour=(random.randint(0,16777215)))
        emb.set_author(name=(member.display_name), icon_url=(member.avatar_url))
        emb.timestamp = datetime.datetime.now()
        emb.set_footer(text="Time > ")
        send_embed = await ctx.send(embed=emb)
        if config.mention_all == True:
            msg = await ctx.send("<@everyone>")
            await msg.delete()
        await ctx.message.delete()

async def setup(bot:commands.Bot):
	await bot.add_cog(Announce(bot))