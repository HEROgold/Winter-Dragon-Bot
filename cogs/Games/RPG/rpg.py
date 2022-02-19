import discord, json, os
from discord.ext import commands

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
    async def Setup(self, ctx):
        data = await get_data()
        if not str(ctx.author.id) in data:
            data[ctx.author.id] = {}
            data[ctx.author.id]['name'] = str(ctx.author.name)
            data[ctx.author.id]['balance'] = 115
            data[ctx.author.id]['level'] = 1
            data[ctx.author.id]['experience'] = {}
            data[ctx.author.id]['experience']['total'] = 20
            data[ctx.author.id]['experience']['defense'] = 0
            data[ctx.author.id]['experience']['hp'] = 0
            data[ctx.author.id]['experience']['strength'] = 0
            data[ctx.author.id]['experience']['stamina'] = 0
            data[ctx.author.id]['experience']['brewing'] = 0
            data[ctx.author.id]['experience']['speed'] = 10
            data[ctx.author.id]['experience']['accuracy'] = 10
            data[ctx.author.id]['inventory'] = {}
            data[ctx.author.id]['inventory']['hp-potion'] = {}
            data[ctx.author.id]['inventory']['hp-potion']['amount'] = 5
            data[ctx.author.id]['inventory']['hp-potion']['healing'] = 3
            data[ctx.author.id]['inventory']['short-sword'] = {}
            data[ctx.author.id]['inventory']['short-sword']['trait'] = {}
            data[ctx.author.id]['inventory']['short-sword']['trait']['name'] = "basic"
            data[ctx.author.id]['inventory']['short-sword']['trait']['damage'] = 0
            data[ctx.author.id]['inventory']['short-sword']['trait']['accuracy'] = 5
            data[ctx.author.id]['inventory']['short-sword']['damage'] = 1
            data[ctx.author.id]['inventory']['short-sword']['accuracy'] = 75
            data[ctx.author.id]['inventory']['short-sword']['weight'] = 5
            await ctx.send("Your account is set up now.")
        else:
            ctx.send("Your account is already set up.")
        await set_data(data)

    @commands.command(aliases=['level','stats'], brief="View your levels", description="Use this command to show view your current levels")
    async def _stats(self, ctx):
        data = await get_data()
        emb = discord.Embed(title="Levels", description="All your levels!", colour=0x00ffff)
        emb.set_author(name=(ctx.author.display_name), icon_url=(ctx.author.avatar_url))
        exp = data[str(ctx.author.id)]['experience']
        emb.add_field(name="Total", value=(int(exp['total']) / 1000), inline=True)
        emb.add_field(name="Hp", value=(int(exp['hp']) / 100), inline=True)
        emb.add_field(name="Defense", value=(int(exp['defense']) / 100), inline=True)
        emb.add_field(name="Strength", value=(int(exp['strength']) / 100), inline=True)
        emb.add_field(name="Stamina", value=(int(exp['stamina']) / 100), inline=True)
        emb.add_field(name="Brewing", value=(int(exp['brewing']) / 100), inline=True)
        emb.add_field(name="Speed", value=(int(exp['speed']) / 100), inline=True)
        emb.add_field(name="Accuracy", value=(int(exp['accuracy']) / 100), inline=True)
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
