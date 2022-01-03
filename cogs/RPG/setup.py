import discord
from discord.ext import commands
import json
import os

class RPG_Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not os.path.exists('./Database/RPG.json'):
            with open("./Database/RPG.json", "w") as fdb:
                fdb.close
                print("RPG Json Created.")
        else:
            print("RPG Json Loaded.")

    @commands.command()
    async def Setup(self, ctx):
        data = await get_data()
        if not ctx.author.id in data:
            data[ctx.author.id] = {}
            data[ctx.author.id]['name'] = str(ctx.author.name)
            data[ctx.author.id]['balance'] = 115
            data[ctx.author.id]['level'] = 1
            data[ctx.author.id]['experience'] = 0
            data[ctx.author.id]['inventory'] = {}
        await set_data(data)

def setup(bot):
	bot.add_cog(RPG_Setup(bot))

async def get_data():
    with open('.\\Database/RPG.json', 'r') as f:
        gdata = json.load(f)
    return gdata

async def set_data(data):
    with open('.\\Database/RPG.json','w') as f:
         json.dump(data, f)
