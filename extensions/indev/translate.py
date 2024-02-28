
import discord
import flag
import openai

from _types.bot import WinterDragon
from _types.cogs import Cog
from tools.config_reader import config


class Translate(Cog):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        openai.api_key = config["Tokens"]["open_api_key"]


    @Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, member: discord.Member | discord.User) -> None:
        if member.bot is True:
            return

        if not reaction.emoji.is_unicode_emoji():
            return

        land_code = flag.dflagize(reaction.emoji, subregions=False)[1:-1] # type: ignore

        land_code_target_length = 2
        if len(land_code) != land_code_target_length:
            self.logger.critical(f"land code other then 2: {land_code=}")
            return

        clean_content = reaction.message.clean_content

        self.logger.debug(f"translating message for {member}: {reaction.message}")
        if len(clean_content) >= config.getint("Translate", "limit"):
            emb = discord.Embed(title="Cannot Translate", description="The message is too long to translate")
        else:
            emb = self.get_response(member, land_code, clean_content)

        if config.getboolean("Translate", "dm_instead") is True:
            await member.send(embed=emb)
        else:
            await reaction.message.reply(embed=emb)


    # TODO: fix this func
    def get_response(
        self,
        member: discord.Member | discord.User,
        land_code: str,
        clean_content: str,
    ) -> discord.Embed:
        response = openai.Completion.create(
                model= "text-davinci-003",
                prompt= f"Translate `{clean_content}` into {land_code}",
                temperature=0.3,
                max_tokens=config["Translate"]["limit"],
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )
        translated_message = response["choices"][0]["text"]

        emb = discord.Embed(title="Translated Text", description=translated_message)
        emb.set_author(name=(member.display_name), icon_url=(member.avatar.url))

        return emb


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Translate(bot))
