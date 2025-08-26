"""Tournament management extension for the Winter Dragon Bot."""
from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Interaction, app_commands
from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.extensions.tournaments.strategies.single_elimination import SingleEliminationStrategy
from winter_dragon.database.tables.tournament import Tournament


if TYPE_CHECKING:
    from winter_dragon.bot._types.kwargs import BotArgs
    from winter_dragon.bot.core.bot import WinterDragon
    from winter_dragon.bot.extensions.tournaments.strategies.base import TournamentStrategy

class Messages:
    """Messages used in the Tournament Manager."""

    created_tournament = "Tournament Created!"


class TournamentManager(Cog):
    """Cog for managing existing tournaments."""

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the Games cog."""
        super().__init__(**kwargs)

    tournament = app_commands.Group(name="tournament", description="Manage tournaments")

    @tournament.command(name="create")
    async def slash_create(self, interaction: Interaction, strategy: TournamentStrategy | None = None) -> None:
        """Create a new tournament. Default strategy to single elimination."""
        tournament = Tournament(id=interaction.id)
        if strategy is None:
            strategy = SingleEliminationStrategy(tournament, self.session)

        await interaction.response.send_message(Messages.created_tournament)



async def setup(bot: WinterDragon) -> None:
    """Set up function for the tournament manager cog."""
    await bot.add_cog(TournamentManager(bot=bot))
