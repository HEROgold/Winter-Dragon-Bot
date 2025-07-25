"""Tournament strategy base classes and implementations."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from winter_dragon.database.tables import Tournament, TournamentMatch, TournamentTeam


class TournamentStrategy(ABC):
    """Base class for tournament strategies."""
    
    def __init__(self, tournament: Tournament) -> None:
        """Initialize the tournament strategy."""
        self.tournament = tournament
    
    @abstractmethod
    async def generate_matches(self, teams: list[TournamentTeam]) -> list[TournamentMatch]:
        """Generate matches for the tournament."""
        pass
    
    @abstractmethod
    async def advance_to_next_round(self, completed_matches: list[TournamentMatch]) -> list[TournamentMatch]:
        """Advance tournament to the next round based on completed matches."""
        pass
    
    @abstractmethod
    def is_tournament_complete(self, teams: list[TournamentTeam], matches: list[TournamentMatch]) -> bool:
        """Check if the tournament is complete."""
        pass
    
    @abstractmethod
    def get_standings(self, teams: list[TournamentTeam], matches: list[TournamentMatch]) -> list[TournamentTeam]:
        """Get current tournament standings."""
        pass
    
    def validate_team_count(self, team_count: int) -> bool:
        """Validate if the team count is valid for this tournament type."""
        return team_count >= 2