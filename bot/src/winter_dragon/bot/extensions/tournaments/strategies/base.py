"""Tournament strategy base classes and implementations."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from sqlmodel import Session

from winter_dragon.bot.core.log import LoggerMixin
from winter_dragon.bot.extensions.tournaments.strategies.errors import InvalidTeamCountError


if TYPE_CHECKING:
    from winter_dragon.database.tables import Tournament, TournamentMatch, TournamentTeam
import re


class TournamentStrategy(ABC, LoggerMixin):
    """Base class for tournament strategies."""

    def __init_subclass__(cls) -> None:
        """Initialize the tournament strategy subclass."""
        cls.random = random.Random()  # noqa: S311
        cls.logger.debug(f"{cls.random.seed=}")
        return super().__init_subclass__()

    def __init__(self, tournament: Tournament, session: Session) -> None:
        """Initialize the tournament strategy."""
        self.tournament = tournament
        self.session = session

    @property
    @abstractmethod
    def min_team_count(self) -> int:
        """Minimum team count required for the tournament."""
        return 2

    @property
    @abstractmethod
    def teams(self) -> list[TournamentTeam]:
        """List of teams participating in the tournament."""
        return []

    @abstractmethod
    async def generate_matches(self, teams: list[TournamentTeam]) -> list[TournamentMatch]:
        """Generate matches for the tournament."""

    @abstractmethod
    async def advance(self, completed_matches: list[TournamentMatch]) -> list[TournamentMatch]:
        """Advance tournament team's to the next round based on completed matches."""

    @abstractmethod
    def is_complete(self, teams: list[TournamentTeam], matches: list[TournamentMatch]) -> bool:
        """Check if the tournament is complete."""

    @abstractmethod
    def get_standings(self, teams: list[TournamentTeam], matches: list[TournamentMatch]) -> list[TournamentTeam]:
        """Get current tournament standings."""

    def validate_team_count(self) -> bool:
        """Validate if the team count is valid for this tournament type."""
        if len(self.teams) < self.min_team_count:
            # Split at capital letters and join with spaces
            readable_name = " ".join(re.findall(r"[A-Z][a-z]*", self.__class__.__name__))

            msg = (
                f"Not enough teams to start a {readable_name} tournament.\n"
                f"Minimum required: {self.min_team_count}, Current: {len(self.teams)}"
            )
            raise InvalidTeamCountError(msg)
        return True
