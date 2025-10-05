"""Module for tracking games."""
from collections.abc import Sequence
from typing import Unpack

import discord
from discord import app_commands
from sqlmodel import select
from winter_dragon.bot._types.kwargs import BotArgs

from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.database.tables import Games as GamesDB
from winter_dragon.database.tables import Suggestions


class Games(GroupCog):
    """Cog that tracks known games and allows users to suggest new ones."""

    games: Sequence[GamesDB]

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the Games cog."""
        super().__init__(**kwargs)
        self.games = self.session.exec(select(GamesDB)).all()


    @app_commands.command(name="list", description="Get a list of known games")
    async def slash_list(self, interaction: discord.Interaction) -> None:
        """Get a list of known games."""
        await interaction.response.send_message(", ".join(map(str, self.games)), ephemeral=True)


    @app_commands.command(name="suggest", description="Suggest a new game to be added")
    async def slash_suggest(self, interaction: discord.Interaction, name: str) -> None:
        """Suggest a new game to be added."""
        for suggestion in self.session.exec(select(Suggestions).where(Suggestions.type == "game")).all():
            if suggestion.content == name:
                await interaction.response.send_message("That game is already in review", ephemeral=True)

        self.session.add(Suggestions(
            type = "game",
            verified_at = None,
            content = name,
        ))
        self.session.commit()
        await interaction.response.send_message(f"Added `{name}` for review", ephemeral=True)


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(Games(bot=bot))
