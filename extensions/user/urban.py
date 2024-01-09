import discord
import requests
import urllib.parse
import logging

from discord import app_commands

from tools.config_reader import config
from _types.cogs import GroupCog
from _types.bot import WinterDragon


class Urban(GroupCog):
    def __init__(self, bot) -> None:
        self.bot: WinterDragon = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")


    @app_commands.command(
        name="random",
        description="get random definitions"
    )
    async def slash_urban_random(self, interaction: discord.Interaction) -> None:
        if config["Urban"]["ALLOW_RANDOM"] is True:
            UD_RANDOM_URL = 'http://api.urbandictionary.com/v0/random'
            response = requests.get(UD_RANDOM_URL)
            json = response.json()
            random_list:list[dict] = json["list"]
            self.logger.debug(f"{random_list}")
            emb = discord.Embed(title="Dictionary Random")
            emb.set_footer(text="Results are from an API!")
            emb.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar)
            for i, r in enumerate(random_list, start=1):
                if i <= config.Urban.MAX_LENGTH:
                    word = r["word"]
                    definition = r["definition"]
                    urban_url = r["permalink"]
                    self.logger.debug(f"word: {word}, definition: {definition}")
                    emb.add_field(name=word, value=f"{definition}\n{urban_url}", inline=True)
            await interaction.response.send_message(embed=emb)
        else:
            await interaction.response.send_message("Random definitions are disabled", ephemeral=True)


    @app_commands.command(
        name="search",
        description="Look into urban dictionary for a meaning and its definition."
        )
    async def slash_urban(self, interaction: discord.Interaction, query: str) -> None:
        UD_DEFINE_URL = 'http://api.urbandictionary.com/v0/define?term='
        response = requests.get(UD_DEFINE_URL + urllib.parse.quote(query))
        json = response.json()
        defined = json["list"]
        self.logger.debug(f"defined: {defined}")
        if len(defined) > 1:
            emb = discord.Embed(title=f"Dictionary Search: {query}")
            emb.set_footer(text="Results are from api.urbandictionary.com")
            emb.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar)
            emb.add_field(name="1", value=defined[0]["definition"], inline=True)
            emb.add_field(name="2", value=defined[1]["definition"], inline=True)
            emb.add_field(name="|", value="|", inline=False)
            emb.add_field(name="Votes 1:", value=f":thumbsup: {str(defined[0]['thumbs_up'])} :thumbsdown:{str(defined[0]['thumbs_down'])}", inline=True)
            emb.add_field(name="Votes 2:", value=f":thumbsup: {str(defined[1]['thumbs_up'])} :thumbsdown:{str(defined[1]['thumbs_down'])}", inline=True)
            await interaction.response.send_message(embed=emb)
        elif len(defined) == 1:
            emb = discord.Embed(title=f"Dictionary Search {query}")
            emb.set_footer(text="Results are from an API!")
            emb.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
            emb.add_field(name="1", value=defined[0]["definition"], inline=False)
            emb.add_field(name="Votes 1:", value=f":thumbsup: {str(defined[0]['thumbs_up'])} :thumbsdown:{str(defined[0]['thumbs_down'])}", inline=False)
            await interaction.response.send_message(embed=emb)
        else:
            await interaction.response.send_message("No results found.")


async def setup(bot: WinterDragon) -> None:
	await bot.add_cog(Urban(bot))
