import discord
from discord.ext import commands
import asyncio
import datetime
import random
from config import reminder as config

class Reminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #lots of time converters inside command, then send message and wait the needed time to remind the user.
    @commands.command(aliases=("remind","remember"), pass_context=True, brief="Usage: reminder (time) (message)", description="Set a reminder for yourself!, Time must end with s, h, d, m for seconds, hours, days, months.")
    async def reminder(self, ctx, time, *, reminder=None):
        print(time)
        print(reminder)
        member = ctx.message.author
        embed = discord.Embed(colour=(random.randint(0,16777215)))
        seconds = 0
        dm = await member.create_dm()
        if reminder is None:
            embed.add_field(name='Warning', value='Please specify what do you want me to remind you about.') # Error message
        if time.lower().endswith("d"):
            seconds += int(time[:-1]) * 60 * 60 * 24
            counter = f"{seconds // 60 // 60 // 24} days"
        if time.lower().endswith("h"):
            seconds += int(time[:-1]) * 60 * 60
            counter = f"{seconds // 60 // 60} hours"
        elif time.lower().endswith("m"):
            seconds += int(time[:-1]) * 60
            counter = f"{seconds // 60} minutes"
        elif time.lower().endswith("s"):
            seconds += int(time[:-1])
            counter = f"{seconds} seconds"
        if seconds == 0:
            embed.add_field(name='Warning', value='Please specify a proper duration, example: remind 5d give cactus water')
        elif seconds < 60:
            embed.add_field(name='Warning',
                            value='You have specified a too short duration!\nMinimum duration is {config.min_duration} minute(ss).')
        elif seconds > 31556926:
            embed.add_field(name='Warning', value='You have specified a too long duration!\nMaximum duration is {config.max_duration} days(s).')
        else:
            await dm.send(f"I will remind you about {reminder} in {counter}.")
            await asyncio.sleep(seconds)
            await dm.send(f"Hi, you asked me to remind you about {reminder}, {counter} ago.")
            return
        
        await dm.send(embed=embed)

def setup(bot):
	bot.add_cog(Reminder(bot))