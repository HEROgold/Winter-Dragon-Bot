import discord, os, json
from discord.ext import commands

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not os.path.exists('./Database/Stats.json'):
            with open("./Database/Stats.json", "w") as f:
                json.dump("{}", f)
                f.close
                print("Stats Json Created.")
        else:
            print("Stats Json Loaded.")

    #@commands.Cog.listener()
    #EVENt LISTENER EXAPLE!

    @commands.command() # show some guild/server stats
    @commands.has_permissions(manage_channels=True)
    async def stats(self, ctx):
        guild = ctx.guild
        overwrite = {
            ctx.guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
            ctx.guild.me: discord.PermissionOverwrite(connect=True)
            }
        member_count = guild.member_count
        data = await get_data()
        if not str(guild.id) in data:
            category = await guild.create_category(name="Stats", overwrites=overwrite)
            member_channel = await category.create_voice_channel(name="0 Members")
            online_channel = await category.create_voice_channel(name="0 Online Users")
            user_channel = await category.create_voice_channel(name="0 Total Users")
            guild_channel = await category.create_voice_channel(name="0 Days Old")
            time_channel = await category.create_voice_channel(name="0 GMT")

            data[guild.id] = {}
            data[guild.id]["category"] = category.id
            data[guild.id]["channels"] = {}
            data[guild.id]["channels"]["member_channel"] = member_channel.id
            data[guild.id]["channels"]["online_channel"] = online_channel.id
            data[guild.id]["channels"]["user_channel"] = user_channel.id
            data[guild.id]["channels"]["guild_channel"] = guild_channel.id
            data[guild.id]["channels"]["time_channel"] = time_channel.id

        await set_data(data)
        await ctx.send(f"Stats Channels Are Set Up")


    @commands.command() # Delete Setup Server Stats, Fix loop if statement. Maybe rewrite code. Compare specific key, value
    @commands.has_permissions(manage_channels=True)
    async def remove_stats(self, ctx):
        guild = ctx.guild
        data = await get_data
        for k,v in data.items():
            if v == guild.id: # ERROR IS HERE THE IF STATEMENT
                print(k, v)
                channel = await bot.get_channel(v)
                await channel.delete()

async def get_data():
    with open('.\\Database/Stats.json', 'r') as f:
        data = json.load(f)
    return data

async def set_data(data):
    with open('.\\Database/Stats.json','w') as f:
         json.dump(data, f)

def setup(bot):
	bot.add_cog(Stats(bot))