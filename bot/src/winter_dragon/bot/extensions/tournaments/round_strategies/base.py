"""Tournament strategy base classes and implementations."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar


if TYPE_CHECKING:
    from collections.abc import Sequence

    import discord
    from winter_dragon.database.tables import Tournament, TournamentMatch, TournamentTeam




class TournamentStrategy(ABC):
    """Base class for tournament strategies."""

    REQUIRED_TEAM_SIZE: ClassVar[int] = 2

    def __init__(self, tournament: Tournament) -> None:
        """Initialize the tournament strategy."""
        self.tournament = tournament

    @abstractmethod
    async def generate_matches(self, teams: Sequence[TournamentTeam]) -> Sequence[TournamentMatch]:
        """Generate matches for the tournament."""

    @abstractmethod
    async def advance_to_next_round(self, completed_matches: Sequence[TournamentMatch]) -> Sequence[TournamentMatch]:
        """Advance tournament to the next round based on completed matches."""

    @abstractmethod
    def is_tournament_complete(self, teams: Sequence[TournamentTeam], matches: Sequence[TournamentMatch]) -> bool:
        """Check if the tournament is complete."""

    @abstractmethod
    def get_standings(self, teams: Sequence[TournamentTeam], matches: Sequence[TournamentMatch]) -> list[TournamentTeam]:
        """Get current tournament standings."""

    @abstractmethod
    def generate_bracket(self, teams: Sequence[TournamentTeam]) -> Sequence[TournamentMatch]:
        """Generate the tournament bracket based on the teams participating."""

    @abstractmethod
    def generate_standings_message(self, embed: discord.Embed) -> discord.Embed:
        """Generate the embed with tournament standings information."""

    def validate_team_count(self, team_count: int) -> bool:
        """Validate if the team count is valid for this tournament type."""
        return team_count >= self.REQUIRED_TEAM_SIZE
