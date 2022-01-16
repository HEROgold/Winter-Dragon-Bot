import discord, os, json, asyncio, datetime
from discord.ext import commands
#from config import stats as config

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not os.path.exists('./Database/Stats.json'):
            with open("./Database/Stats.json", "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                print("Stats Json Created.")
        else:
            print("Stats Json Loaded.")

    @commands.Cog.listener()
    async def on_ready(self):
        while True:
            await self.update()
            await asyncio.sleep(60*5)# timer to fight ratelimits
            

    @commands.command()
    async def reset_stats(self, ctx):
        if ctx.message.author.id == mainconfig.owner_id:
            data = await get_data()
            for guild in self.bot.guilds:
                if str(guild.id) in data:
                    await self.remove_stats(ctx=ctx, guild=guild)
                    await self.stats(ctx=ctx, guild=guild)

    async def update(self):
        data = await get_data()
        guilds = self.bot.guilds
        for guild in guilds:
            if str(guild.id) in data:
                await asyncio.sleep(1) # timer between guilds to fight ratelimits
                guild_id = data[str(guild.id)]
                category = list(guild_id.values())[0]
                channels = list(category.values())[0]
                users = sum(member.bot==False for member in guild.members)
                bots = sum(member.bot==True for member in guild.members)
                online = sum(member.status!=discord.Status.offline and not member.bot for member in guild.members)
                age = guild.created_at.strftime("%Y-%m-%d")
                time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                online_channel = category["channels"]["online_channel"]
                user_channel = category["channels"]["user_channel"]
                bot_channel = category["channels"]["bot_channel"]
                guild_channel = category["channels"]["guild_channel"]
                time_channel = category["channels"]["time_channel"]
                await self.bot.get_channel(time_channel).edit(name=(str(time) + " UTC"))
                await self.bot.get_channel(online_channel).edit(name=(str(online) + " Online Users"))
                await self.bot.get_channel(user_channel).edit(name=(str(users) + " Total Users"))
                await self.bot.get_channel(bot_channel).edit(name=(str(bots) + " Online Bots"))
                await self.bot.get_channel(guild_channel).edit(name=(str(age) + " Creation Date."))

    @commands.command(brief="Create the Stats category", description="This command will create the Stats category which will show some stats about the server.") # show some guild/server stats
    @commands.has_permissions(manage_channels=True)
    async def stats_category(self, ctx, guild=None):
        if guild == None:
            guild = ctx.guild
        overwrite = {
            ctx.guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
            ctx.guild.me: discord.PermissionOverwrite(connect=True)
            }
        member_count = guild.member_count
        data = await get_data()
        if not str(guild.id) in data:
            category = await guild.create_category(name="Stats", overwrites=overwrite, position=0)
            online_channel = await category.create_voice_channel(name="0 Online Users")
            user_channel = await category.create_voice_channel(name="0 Total Users")
            bot_channel = await category.create_voice_channel(name="0 Total Bots")
            guild_channel = await category.create_voice_channel(name="0 Creation Date")
            time_channel = await category.create_voice_channel(name="0 UTC")

            data[guild.id] = {}
            data[guild.id][category.id] = {}
            data[guild.id][category.id]["channels"] = {}
            data[guild.id][category.id]["channels"]["category_channel"] = category.id
            data[guild.id][category.id]["channels"]["online_channel"] = online_channel.id
            data[guild.id][category.id]["channels"]["user_channel"] = user_channel.id
            data[guild.id][category.id]["channels"]["bot_channel"] = bot_channel.id
            data[guild.id][category.id]["channels"]["guild_channel"] = guild_channel.id
            data[guild.id][category.id]["channels"]["time_channel"] = time_channel.id
            await ctx.send(f"Stats channels are set up")
        else:
            await ctx.send("Stats channels arleady set up")
        await set_data(data)

    @commands.command(brief="Remove the Stats channels", description="This command removes the stat channels from your discord server. This includes the Category as well as all channels in that.") 
    @commands.has_permissions(manage_channels=True)
    async def remove_stats_category(self, ctx, guild=None):
        if guild == None:
            guild = ctx.guild
        data = await get_data()
        if not str(guild.id) in data:
            await ctx.send("No stats stats found to remove.")
        else:
            guild = data[str(guild.id)]
            category = list(guild.values())[0]
            channels = list(category.values())[0]
            print(channels)
            for k, v in channels.items():
                channel = self.bot.get_channel(v)
                await channel.delete()
            del data[str(ctx.guild.id)]
        await set_data(data)

async def get_data():
    with open('.\\Database/Stats.json', 'r') as f:
        data = json.load(f)
    return data

async def set_data(data):
    with open('.\\Database/Stats.json','w') as f:
         json.dump(data, f)

def setup(bot):
	bot.add_cog(Stats(bot))