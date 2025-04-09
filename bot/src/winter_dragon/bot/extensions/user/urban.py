"""Urban Dictionary cog for Discord bot."""

import asyncio
import urllib.parse

import discord
import requests
from discord import app_commands
from winter_dragon.bot.config import Config, config
from winter_dragon.bot.constants import UD_DEFINE_URL, UD_RANDOM_URL
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.core.log import LoggerMixin


class Urban(GroupCog, LoggerMixin):
    """Urban Dictionary cog for Discord bot."""

    def __init__(self, bot: WinterDragon) -> None:
        """Initialize the Urban cog."""
        self.bot = bot
        self.loop = asyncio.get_event_loop()

    async def _get_response(self, url: str) -> requests.Response:
        return await self.loop.run_in_executor(None, requests.get, url)

    @app_commands.command(name="random", description="get random definitions")
    @Config.default("Urban", "allow_random", True)  # noqa: FBT003
    async def slash_urban_random(self, interaction: discord.Interaction) -> None:
        """Get a random definition from the Urban Dictionary."""
        allowed_random = config.getboolean("Urban", "allow_random")
        if allowed_random is False:
            await interaction.response.send_message("Random definitions are disabled", ephemeral=True)
            return
        response = await self._get_response(UD_RANDOM_URL)
        json = response.json()
        random_list: list[dict[str, str]] = json["list"]
        self.logger.debug(f"{random_list}")
        emb = discord.Embed(title="Dictionary Random")
        emb.set_footer(text="Results are from an API!")
        emb.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar)
        for i, r in enumerate(random_list, start=1):
            if i <= config.getint("Urban", "MAX_LENGTH"):
                word = r["word"]
                definition = r["definition"]
                urban_url = r["permalink"]
                self.logger.debug(f"word: {word}, definition: {definition}")
                emb.add_field(name=word, value=f"{definition}\n{urban_url}", inline=True)
        await interaction.response.send_message(embed=emb)


    @app_commands.command(
        name="search",
        description="Look into urban dictionary for a meaning and its definition.",
    )
    async def slash_urban(self, interaction: discord.Interaction, query: str) -> None:
        """Search for a word in the Urban Dictionary."""
        response = await self._get_response(UD_DEFINE_URL + urllib.parse.quote(query))
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
            emb.add_field(
                name="Votes 1:",
                value=f":thumbsup: {defined[0]['thumbs_up']!s} :thumbsdown:{defined[0]['thumbs_down']!s}",
                inline=True,
            )
            emb.add_field(
                name="Votes 2:",
                value=f":thumbsup: {defined[1]['thumbs_up']!s} :thumbsdown:{defined[1]['thumbs_down']!s}",
                inline=True,
            )
            await interaction.response.send_message(embed=emb)
        elif len(defined) == 1:
            emb = discord.Embed(title=f"Dictionary Search {query}")
            emb.set_footer(text="Results are from an API!")
            avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
            emb.set_author(name=interaction.user.display_name, icon_url=avatar_url)
            emb.add_field(name="1", value=defined[0]["definition"], inline=False)
            emb.add_field(
                name="Votes 1:",
                value=f":thumbsup: {defined[0]['thumbs_up']!s} :thumbsdown:{defined[0]['thumbs_down']!s}",
                inline=False,
            )
            await interaction.response.send_message(embed=emb)
        else:
            await interaction.response.send_message("No results found.")


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(Urban(bot))
