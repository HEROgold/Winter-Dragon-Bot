"""Module containing the looking for group cog."""
from typing import Unpack

import discord
from discord import app_commands
from sqlmodel import select
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.extensions.games.games import Games
from winter_dragon.bot.settings import Settings
from winter_dragon.database.tables import Games as GamesDB
from winter_dragon.database.tables import LookingForGroup

from bot.src.winter_dragon.bot._types.kwargs import BotKwarg


@app_commands.guilds(Settings.support_guild_id)
class Lfg(GroupCog):
    """LFG cog for finding people to play games with."""

    slash_suggest = Games.slash_suggest


    def __init__(self, **kwargs: Unpack[BotKwarg]) -> None:
        """Initialize the LFG cog."""
        super().__init__(**kwargs)
        self.games = [i.name for i in self.session.exec(select(GamesDB)).all()]

    # TODO: add Database table, matching user id and category, every time someone adds, check matches.
    @app_commands.command(name="join", description="Join a search queue for finding people for the same game")
    async def slash_lfg_join(self, interaction: discord.Interaction, game: str) -> None:
        """Join a search queue for finding people for the same game."""
        game_db = self.session.exec(select(GamesDB).where(GamesDB.name == game)).first()
        if game_db is None:
            await interaction.response.send_message("This game is not supported", ephemeral=True)
            return
        total = self.session.exec(select(LookingForGroup).where(LookingForGroup.game_name == game)).all()
        self.session.add(LookingForGroup(
                user_id = interaction.user.id,
                game_name = game_db.name,
            ))
        self.session.commit()
        c_mention = self.get_command_mention(self.slash_lfg_leave)
        msg = f"Adding you to the search queue for {game}, currently there are {len(total)} in the same queue. Use {c_mention} to leave all queues."  # noqa: E501
        await interaction.response.send_message(msg, ephemeral=True)


    @app_commands.command(name="leave", description="leave all joined search queue")
    async def slash_lfg_leave(self, interaction: discord.Interaction) -> None:
        """Leave all joined search queues."""
        lfg = self.session.exec(select(LookingForGroup).where(LookingForGroup.user_id == interaction.user.id)).all()
        for i in lfg:
            self.session.delete(i)
        self.session.commit()
        c_mention = await self.get_command_mention(self.slash_lfg_join)
        await interaction.response.send_message(
            f"Removed you from all lfg queues, use {c_mention} to join one again.",
            ephemeral=True,
        )


    @slash_lfg_join.autocomplete("game")
    async def autocomplete_game(
        self,
        _interaction:
        discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for the game name."""
        return [
            app_commands.Choice(name=i, value=i)
            for i in self.games
            if current.lower() in i.lower()
        ] or [
            app_commands.Choice(name=i, value=i)
            for i in self.games
        ]


    async def search_match(self, interaction: discord.Interaction, _game: str) -> None:
        """Search for a match in the database."""
        user_games = self.session.exec(select(LookingForGroup).where(LookingForGroup.user_id == interaction.user.id)).all()
        for user_game in user_games:
            lfg_game = self.session.exec(select(LookingForGroup).where(LookingForGroup.game_name == user_game.game_name)).all()
            self.logger.debug(f"{user_game=}, {lfg_game=}")


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(Lfg(bot=bot))
