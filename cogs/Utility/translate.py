import discord, flag, config
from discord.ext import commands
from googletrans import Translator

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, member):
        print(reaction.emoji)
        translator = Translator()
        landcode = flag.dflagize(reaction.emoji)[1:-1]
        try:
            translated = translator.translate(reaction.message.content, dest=landcode)
            emb = discord.Embed(title="Original Text", description=reaction.message.content)
            emb.set_author(name=(member.display_name), icon_url=(member.avatar_url))
            emb.add_field(name=f"Translated:", value=translated.text, inline=True)
            if config.translate.dm_instead == True:
                dm = await member.create_dm()
                await dm.send(embed=emb)
            else:
                await reaction.message.channel.send(embed=emb)
        except Exception:
            print(f"Translate React Error: {Exception}")
            pass
    
def setup(bot):
	bot.add_cog(Translate(bot))