import discord, os, json, datetime
from discord.ext import commands

class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not os.path.exists('./Database/Ban.json'):
            with open("./Database/Ban.json", "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                print("Ban Json Created.")
        else:
            print("Ban Json Loaded.")

    @commands.has_permissions(manage_roles=True, ban_members=True)
    @commands.command(brief="Ban a user for X amount of time. Min: 1m", description="Ban a user form the server for a specified amount of time.")
    async def ban(self, ctx, user , time= "1d", *, reason = "unspecified"):
        data = await get_data()
        users = ctx.message.mentions
        role_list, find = [], []
        seconds = 0
        if time is None:
            embed.add_field(name='Warning', value='Please specify what do you want me to remind you about.') # Error message
        if time.lower().endswith("d"):
            seconds += int(time[:-1]) * 60 * 60 * 24
        if time.lower().endswith("h"):
            seconds += int(time[:-1]) * 60 * 60
        elif time.lower().endswith("m"):
            seconds += int(time[:-1]) * 60
        elif time.lower().endswith("s"):
            seconds += int(time[:-1])
        if seconds < 60:
            await ctx.send("The ban is not not enough. A minimum of 1 minute is required")
        release_date = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        for role in ctx.guild.roles:
            if role.name == "Banned":
                find.append(role.name)
        if not find:
            await ctx.guild.create_role(name="Banned",
                                        colour=discord.Colour(0xffffff),
                                        reason="Added the ban role so you can ban users from interacting with this server without removing them from the server list.",
                                        permissions=discord.Permissions(0))
        for user in users:
            if not user.bot:
                for role in user.roles:
                    role_list.append(role.id)
        if not str(user.id) in data:
            data[user.id] = {}
            data[user.id][ctx.guild.id] = {}
            data[user.id][ctx.guild.id]["release_date"] = str(release_date)
            data[user.id][ctx.guild.id]["roles"] = []
            data[user.id][ctx.guild.id]["roles"] = role_list
            await user.edit(roles=[role])
        await user.add_roles(discord.utils.get(ctx.guild.roles, name = "Banned"))    
        await set_data(data)

    @commands.has_permissions(manage_roles=True, ban_members=True)
    @commands.command(brief="Unban a banned user", description="Unban a user that has been banned.")
    async def unban(self, ctx, user, *, reason = "unspecified"):
        data = await get_data()
        users = ctx.message.mentions
        for user in users:
            if not user.bot:
                if str(user.id) in data:
                    role_id = data[str(user.id)][str(ctx.guild.id)]["roles"]
                    for role in role_id:
                        try:
                            await user.add_roles(discord.utils.get(ctx.guild.roles, id=role))
                        except:
                            print(Exception)

async def get_data():
    with open('.\\Database/Ban.json', 'r') as f:
        data = json.load(f)
    return data

async def set_data(data):
    with open('.\\Database/Ban.json','w') as f:
         json.dump(data, f)


def setup(bot):
	bot.add_cog(Ban(bot))

#date_time_str = '18/09/19 01:55:19'
#
#date_time_obj = datetime.strptime(date_time_str, '%d/%m/%y %H:%M:%S')
#
#
#print ("The type of the date is now",  type(date_time_obj))
#print ("The date is", date_time_obj)