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

    @commands.command(brief="WIP", description="WIP")
    async def Uno(self, ctx):
        red = (255,0,0)
        green =(0,255,0)
        blue = (0,0,255)
        yellow = (255,255,0)
        P1, P2, P3, P4 = "1234"
        player_emojis = (916396145901711421, 916396145918496809, 916396145503244409, 916396146472124456) # Temp usage of Id's! > Change to create custom emoji's and save those in DB per server/user.
        colours = [red, green, yellow, blue]
        game_id = random.randrange(0,99999) # TEMP change and use this for DB acces.
        r,g,b = random.choice(colours)

        emb = discord.Embed(title=f"Uno Game#{game_id}", description="Join this uno game and try to beat your friends!", color=discord.Color.from_rgb(r,g,b))
        emb.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        emb.add_field(name=P1, value=1, inline=True)
        emb.add_field(name=P2, value=2, inline=True)
        emb.add_field(name=P3, value=3, inline=True)
        emb.add_field(name=P4, value=4, inline=True)
        send_embed = await ctx.send(embed=emb)
        await ctx.message.delete()

        for i in player_emojis:
            await send_embed.add_reaction(ctx.bot.get_emoji(i))

@commands.Cog.listener() #on reaction added to message check if already reacted, then remove reaction if already reacted.
async def on_raw_reaction_add(self, ctx):
    id = ctx.message_id
    member = ctx.user
    if not member.bot:
            if member.id in get_data():
                await message.remove_reaction(emoji, member)
                dm = await member.create_dm()
                await dm.send("Your second reaction has been removed.\n You may only join once!")
            else:
                users.append(member.id)
                print(f"{member.id} added to the uno list {users}")
    else:
        print(f"{member} is a Bot, Cannot add to the uno list")

async def get_data():
    with open('.\\Database/Uno.json', 'r') as f:
        data = json.load(f)
    return data

async def set_data(data):
    with open('.\\Database/Uno.json','w') as f:
         json.dump(data, f)

def setup(bot):
	bot.add_cog(Uno(bot))