import discord, mainconfig
from discord.ext import commands

class bot_announce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #@commands.Cog.listener()
    #EVENt LISTENER EXAPLE!

    @commands.command(brief="Announce important messages on all servers the bot runs on", description="This command will send an announcement to all servers regarding this bot.")
    async def global_announce(self, ctx, *, msg):
        if ctx.message.author.id == mainconfig.owner_id:
            for guild in self.bot.guilds:
                await self.bot.get_channel(guild.public_updates_channel.id).send(msg)

def setup(bot):
	bot.add_cog(bot_announce(bot))