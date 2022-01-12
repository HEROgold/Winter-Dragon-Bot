import discord
from discord.ext import commands
from config import activity as config

class Activity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        status = discord.Status.idle
        type = discord.ActivityType.competing
        activity = discord.Activity(type=type, name="Licking a wedding cake")
        await self.bot.change_presence(status=status, activity=activity)
        print("Activity and status set!")

def setup(bot):
	bot.add_cog(Activity(bot))