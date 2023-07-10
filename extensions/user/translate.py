import logging

import discord
import flag
import openai
from discord.ext import commands

import config


class Translate(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        openai.api_key = config.Tokens.OPEN_API_KEY
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, member: discord.Member | discord.User) -> None:
        if member.bot == True:
            return

        land_code = flag.dflagize(reaction.emoji)[1:-1]

        if len(land_code) != 2:
            self.logger.critical(f"land code longer then 2: {land_code=}")
            return

        dm = member.dm_channel or await member.create_dm()
        clean_content = reaction.message.clean_content

        self.logger.debug(f"translating message for {member}: {reaction.message}")
        if len(clean_content) >= config.Translate.LIMIT:
            emb = discord.Embed(title="Cannot Translate", description="The message is too long to translate")
        else:
            emb = self.get_response(member, land_code, clean_content)

        if config.Translate.DM_INSTEAD == True:
            await dm.send(embed=emb)
        else:
            await reaction.message.reply(embed=emb)


    def get_response(
        self,
        member: discord.Member | discord.User,
        land_code: str,
        clean_content: str
    ) -> discord.Embed:
        response = openai.Completion.create(
                model= "text-davinci-003",
                prompt= f"Translate `{clean_content}` into {land_code}",
                temperature=0.3,
                max_tokens=config.Translate.LIMIT,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
        translated_message = response["choices"][0]["text"]

        emb = discord.Embed(title="Translated Text", description=translated_message)
        emb.set_author(name=(member.display_name), icon_url=(member.avatar.url))

        return emb


async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Translate(bot))
