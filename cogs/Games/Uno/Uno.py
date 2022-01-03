import discord, random, os, json
from discord.ext import commands

class Uno(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not os.path.exists('./Database/Uno.json'):
            with open(".\\Database/Uno.json", "w") as f:
                json.dump("{}", f)
                f.close
                print("Uno Json Created.")
        else:
            print("Uno Json Loaded.")

    #@commands.Cog.listener()
    #EVENt LISTENER EXAPLE!

    @commands.command()
    async def Uno(self, ctx):
        red = (255,0,0)
        green =(0,255,0)
        blue = (0,0,255)
        yellow = (255,255,0)
        P1, P2, P3, P4 = "1234"
        player_emojis = (916396145901711421, 916396145918496809, 916396145503244409, 916396146472124456) # Temp usage of Id's!
        colours = [red, green, yellow, blue]
        game_id = random.randrange(0,99999)
        r,g,b = random.choice(colours)

        emb = discord.Embed(title=f"Uno Game#{game_id}", description="Join this uno game and try to beat your friends!", color=discord.Color.from_rgb(r,g,b))
        emb.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        emb.add_field(name=P1, value=1, inline=True)
        emb.add_field(name=P2, value=2, inline=True)
        emb.add_field(name=P3, value=3, inline=True)
        emb.add_field(name=P4, value=4, inline=True)
        send_embed = await ctx.send(embed=emb)
        await ctx.message.delete()

        #data = await get_data()
        #data[ctx.guild.id] = {}
        #if not ("emoji_setup", "True" in data.items()):
        #data[ctx.guild.id]["emoji_setup"] = True
        #Blue = await ctx.guild.create_custom_emoji(name="Blue_Card", image=".\\cogs/Games/Uno/Uno_Blue")
        #Red = await ctx.guild.create_custom_emoji(name="Red_Card", image=".\\cogs/Games/Uno/Uno_Red.png")
        #Green = await ctx.guild.create_custom_emoji(name="Green_Card", image=".\\cogs/Games/Uno/Uno_Green.png")
        #Yellow = await ctx.guild.create_custom_emoji(name="Yellow_Card", image=".\\cogs/Games/Uno/Uno_Yellow.png")
        #await set_data(data)

        for i in player_emojis:
            await send_embed.add_reaction(ctx.bot.get_emoji(i))

async def get_data():
    with open('.\\Database/Uno.json', 'r') as f:
        data = json.load(f)
    return data

async def set_data(data):
    with open('.\\Database/Uno.json','w') as f:
         json.dump(data, f)

def setup(bot):
	bot.add_cog(Uno(bot))