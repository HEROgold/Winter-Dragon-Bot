from typing import Any
import discord
import flag
import openai

from tools.config_reader import config
from _types.cogs import Cog
from _types.bot import WinterDragon


class Translate(Cog):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        openai.api_key = config["Tokens"]["open_api_key"]


    @Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, member: discord.Member | discord.User) -> None:
        if member.bot == True:
            return

        land_code = flag.dflagize(reaction.emoji)[1:-1]

        if len(land_code) != 2:
            self.logger.critical(f"land code longer then 2: {land_code=}")
            return

        clean_content = reaction.message.clean_content

        self.logger.debug(f"translating message for {member}: {reaction.message}")
        if len(clean_content) >= config["Translate"]["limit"]:
            emb = discord.Embed(title="Cannot Translate", description="The message is too long to translate")
        else:
            emb = self.get_response(member, land_code, clean_content)

        if config["Translate"]["dm_instead"] == True:
            await member.send(embed=emb)
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
                max_tokens=config["Translate"]["limit"],
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
        translated_message = response["choices"][0]["text"]

        emb = discord.Embed(title="Translated Text", description=translated_message)
        emb.set_author(name=(member.display_name), icon_url=(member.avatar.url))

        return emb


async def setup(bot: WinterDragon) -> None:
	await bot.add_cog(Translate(bot))
