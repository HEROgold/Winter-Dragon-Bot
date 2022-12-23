import discord
from discord.ext import commands
from config import purge as config

class Purge(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    @commands.cooldown(config.ratelimit_amount, config.ratelimit_seconds, commands.BucketType.channel)
    @commands.command(aliases=("clean","delete"),
                    pass_context=True,
                    brief="Remove last X amount of messages",
                    description="Try to remove a specified amount of messages `Purge -1` tries to remove all message in a channel. Won't work for old messages.",
                    usage = "`purge [amount]`:\n Examples: `purge -1`,\n`purge 7`"
    ) #Clear X ammount of message in channel
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx:commands.Context, count:int):
        count += 1
        if count == -1:
            await ctx.channel.purge()
            await ctx.send(f"{ctx.author.mention} Killed {count} Messages.", delete_after=config.delete_after)
        elif count <= config.limit:
            await ctx.channel.purge(limit=count)
            await ctx.send(f"{ctx.author.mention} Killed {count} Messages.", delete_after=config.delete_after)
        else:
            await ctx.send(f"Too many message to kill! The limit is set to {config.limit}")

async def setup(bot:commands.Bot):
	await bot.add_cog(Purge(bot))