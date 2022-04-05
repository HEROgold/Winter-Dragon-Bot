import discord, json, os
from discord.ext import commands
import config

## Needs fixing, change to python class based system like:
#class enemy
#class item
#class user/hero

class RPG_Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not os.path.exists('./Database/RPG.json'):
            with open("./Database/RPG.json", "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                print("RPG Json Created.")
        else:
            print("RPG Json Loaded.")

    @commands.cooldown(1, 500, commands.BucketType.user)
    @commands.command(brief="Setup command to setup RPG account", description="Setup command for RPG experience.")
    async def RPGSetup(self, ctx):
        if ctx.message.author.id == config.main.owner_id: # check if user is owner of bot
            data = await get_data()
            for guild in self.bot.guilds:
                for member in guild.members:
                    if not str(member.id) in data:
                        data[member.id] = {}
                        data[member.id]['name'] = str(member.name)
                        data[member.id]['balance'] = 115
                        data[member.id]['level'] = 1
                        data[member.id]['experience'] = {}
                        data[member.id]['experience']['defense'] = 0
                        data[member.id]['experience']['hp'] = 0
                        data[member.id]['experience']['strength'] = 0
                        data[member.id]['experience']['stamina'] = 0
                        data[member.id]['experience']['brewing'] = 0
                        data[member.id]['experience']['speed'] = 10
                        data[member.id]['experience']['accuracy'] = 10
                        exp = data[member.id]['experience']
                        exp['total'] = (int(exp['defense']) + int(exp['hp']) + int(exp['strength']) + int(exp['brewing']) + int(exp['speed']) + int(exp['accuracy']))
                        data[member.id]['inventory'] = {}
                        data[member.id]['inventory']['hp-potion'] = {}
                        data[member.id]['inventory']['hp-potion']['amount'] = 5
                        data[member.id]['inventory']['hp-potion']['healing'] = 3
                        data[member.id]['inventory']['short-sword'] = {}
                        data[member.id]['inventory']['short-sword']['trait'] = {}
                        data[member.id]['inventory']['short-sword']['trait']['name'] = "basic"
                        data[member.id]['inventory']['short-sword']['trait']['damage'] = 0
                        data[member.id]['inventory']['short-sword']['trait']['accuracy'] = 5
                        data[member.id]['inventory']['short-sword']['damage'] = 1
                        data[member.id]['inventory']['short-sword']['accuracy'] = 75
                        data[member.id]['inventory']['short-sword']['weight'] = 5
            await ctx.send("All accounts are set up now.")
            await set_data(data)

    @commands.command(aliases=['level','stats'], brief="View your levels", description="Use this command to show view your current levels")
    async def _stats(self, ctx):
        data = await get_data()
        exp = data[str(ctx.author.id)]['experience']
        exp['total'] = (int(exp['defense']) + int(exp['hp']) + int(exp['strength']) + int(exp['stamina']) + int(exp['brewing']) + int(exp['speed']) + int(exp['accuracy']))
        emb = discord.Embed(title="Levels", description="All your levels!", colour=0x00ffff)
        emb.set_author(name=(ctx.author.display_name), icon_url=(ctx.author.avatar_url))
        emb.add_field(name="Total", value=(int(exp['total']) / 100), inline=True)
        emb.add_field(name="Hp", value=(int(exp['hp']) / 10), inline=True)
        emb.add_field(name="Defense", value=(int(exp['defense']) / 10), inline=True)
        emb.add_field(name="Strength", value=(int(exp['strength']) / 10), inline=True)
        emb.add_field(name="Stamina", value=(int(exp['stamina']) / 10), inline=True)
        emb.add_field(name="Brewing", value=(int(exp['brewing']) / 10), inline=True)
        emb.add_field(name="Speed", value=(int(exp['speed']) / 10), inline=True)
        emb.add_field(name="Accuracy", value=(int(exp['accuracy']) / 10), inline=True)
        await ctx.send(embed=emb)


async def get_data():
    with open('.\\Database/RPG.json', 'r') as f:
        gdata = json.load(f)
    return gdata

async def set_data(data):
    with open('.\\Database/RPG.json','w') as f:
         json.dump(data, f)

def setup(bot):
	bot.add_cog(RPG_Setup(bot))
