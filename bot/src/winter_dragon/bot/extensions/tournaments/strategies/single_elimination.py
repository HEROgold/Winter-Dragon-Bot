"""Single elimination tournament strategy."""
from __future__ import annotations

from sqlmodel import select
from winter_dragon.bot.extensions.tournaments.strategies.errors import CannotAdvanceError, InvalidTeamCountError
from winter_dragon.database.tables import TournamentMatch, TournamentTeam
from winter_dragon.database.tables.tournament_match import TeamMatches

from .base import TournamentStrategy


class SingleEliminationStrategy(TournamentStrategy):
    """Single elimination tournament strategy."""

    def validate_team_count(self) -> bool:
        """Validate team count (must be power of 2 for clean bracket)."""
        super().validate_team_count()
        team_count = len(self.teams)
        return team_count & team_count - 1 == 0

    async def generate_matches(self, teams: list[TournamentTeam]) -> list[TournamentMatch]:
        """Generate first round matches for single elimination."""
        # Shuffle teams for random seeding
        shuffled_teams = teams.copy()
        self.random.shuffle(shuffled_teams)

        new_var = len(shuffled_teams)
        return [
            TournamentMatch(tournament_id=self.tournament.id, match_id=i)
            for i in range(new_var // 2)
        ]

    async def advance(self, completed_matches: list[TournamentMatch]) -> list[TournamentMatch]:
        """Advance to next round based on completed matches."""
        if not completed_matches:
            msg = "No completed matches to advance."
            raise CannotAdvanceError(msg)

        # Get TournamentTeams from the matches.
        completed_match_ids = [m.id for m in completed_matches]
        matches = self.session.exec(
            select(TeamMatches)
            .where(TeamMatches.match_id in completed_match_ids),
        ).all()
        teams = [
            self.session.exec(select(TournamentTeam).where(TournamentTeam.id == team_match.team_id)).first()
            for team_match in matches if team_match is not None
        ]
        teams = [i for i in teams if i is not None]
        if len(teams) % 2 != 0:
            return await self.generate_matches(teams[1:])
        return await self.generate_matches(teams)


    def is_complete(self, teams: list[TournamentTeam], matches: list[TournamentMatch]) -> bool:
        """Check if tournament is complete (only one team remaining)."""

    def get_standings(self, teams: list[TournamentTeam], matches: list[TournamentMatch]) -> list[TournamentTeam]:
        """Get standings for single elimination (winner first, then by elimination round)."""

    @property
    def min_team_count(self) -> int:
        raise NotImplementedError

    @property
    def teams(self) -> list[TournamentTeam]:
        raise NotImplementedError
