import config
import discord
import flag
from discord.ext import commands
import openai


class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot
        openai.api_key = config.translate.api_key

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction:discord.Reaction, member:discord.Member|discord.User):
        if member.bot == True:
            return
        landcode:str = flag.dflagize(reaction.emoji)[1:-1]
        if len(landcode) != 2:
            return
        dm = await member.create_dm()
        clean_content = reaction.message.clean_content
        if len(clean_content) >= config.translate.limit:
            msg = "Cannot translate, the message is too long."
            emb = discord.Embed(title="Cannot Translate", description=msg)
        else:
            response = openai.Completion.create(
                model= "text-davinci-003",
                prompt= f"Translate {clean_content} into {landcode}",
                temperature=0.3,
                max_tokens=config.translate.limit,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            msg = response["choices"][0]["text"]
            emb = discord.Embed(title="Translated Text", description=msg)
            emb.set_author(name=(member.display_name), icon_url=(member.avatar.url))
        if config.translate.dm_instead == True:
            await dm.send(embed=emb)
        else:
            await reaction.message.channel.send(embed=emb)

async def setup(bot:commands.Bot):
	await bot.add_cog(Translate(bot))