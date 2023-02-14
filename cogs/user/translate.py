import discord
import flag
import openai
from discord.ext import commands

import config


class Translate(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        openai.api_key = config.Translate.API_KEY

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction:discord.Reaction, member:discord.Member|discord.User):
        if member.bot == True:
            return
        landcode:str = flag.dflagize(reaction.emoji)[1:-1]
        if len(landcode) != 2:
            return
        dm = await member.create_dm()
        clean_content = reaction.message.clean_content
        if len(clean_content) >= config.Translate.LIMIT:
            emb = discord.Embed(title="Cannot Translate", description="The message is too long to translate")
        else:
            response = openai.Completion.create(
                model= "text-davinci-003",
                prompt= f"Translate {clean_content} into {landcode}",
                temperature=0.3,
                max_tokens=config.Translate.LIMIT,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            msg = response["choices"][0]["text"]
            emb = discord.Embed(title="Translated Text", description=msg)
            emb.set_author(name=(member.display_name), icon_url=(member.avatar.url))
        if config.Translate.DM_INSTEAD == True:
            await dm.send(embed=emb)
        else:
            await reaction.message.channel.send(embed=emb)

async def setup(bot:commands.Bot):
	await bot.add_cog(Translate(bot))