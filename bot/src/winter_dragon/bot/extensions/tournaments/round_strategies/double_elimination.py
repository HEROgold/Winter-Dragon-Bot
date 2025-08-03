"""Double elimination tournament strategy."""
from __future__ import annotations

from typing import TYPE_CHECKING

from winter_dragon.database.tables import TournamentMatch

from .base import TournamentStrategy


if TYPE_CHECKING:
    from collections.abc import Sequence

    from winter_dragon.database.tables import TournamentTeam


class DoubleEliminationStrategy(TournamentStrategy):
    """Double elimination tournament strategy."""

    REQUIRED_TEAM_SIZE = 4  # Minimum teams for double elimination

    def validate_team_count(self, team_count: int) -> bool:
        """Validate team count (must be power of 2 for clean bracket)."""
        return team_count >= self.REQUIRED_TEAM_SIZE and (team_count & (team_count - 1)) == 0

    async def generate_matches(self, teams: Sequence[TournamentTeam]) -> Sequence[TournamentMatch]:
        """Generate first round matches for double elimination (winners bracket)."""
        if len(teams) < self.REQUIRED_TEAM_SIZE:
            return []

        # Shuffle teams for random seeding
        shuffled_teams = teams.copy()
        import random
        random.shuffle(shuffled_teams)

        matches = []
        for i in range(0, len(shuffled_teams), 2):
            if i + 1 < len(shuffled_teams):
                match = TournamentMatch(
                    tournament_id=self.tournament.id,
                    team1_id=shuffled_teams[i].id,
                    team2_id=shuffled_teams[i + 1].id,
                    round_number=1,
                    match_number=(i // 2) + 1,
                    bracket_position=f"WB_R1M{(i // 2) + 1}",  # Winners Bracket Round 1
                )
                matches.append(match)

        return matches

    async def advance_to_next_round(self, completed_matches: Sequence[TournamentMatch]) -> Sequence[TournamentMatch]:
        """Advance to next round in double elimination."""
        if not completed_matches:
            return []

        current_round = max(match.round_number for match in completed_matches)
        current_round_matches = [m for m in completed_matches if m.round_number == current_round]

        next_matches = []

        # Separate winners and losers bracket matches
        wb_matches = [m for m in current_round_matches if m.bracket_position and m.bracket_position.startswith("WB")]
        [m for m in current_round_matches if m.bracket_position and m.bracket_position.startswith("LB")]

        # Process winners bracket
        if wb_matches:
            winners = [m.winner_team_id for m in wb_matches if m.winner_team_id]
            losers = []
            for match in wb_matches:
                if match.winner_team_id:
                    loser_id = match.team1_id if match.winner_team_id == match.team2_id else match.team2_id
                    losers.append(loser_id)

            # Create next winners bracket round
            if len(winners) >= 2:
                for i in range(0, len(winners), 2):
                    if i + 1 < len(winners):
                        match = TournamentMatch(
                            tournament_id=self.tournament.id,
                            team1_id=winners[i],
                            team2_id=winners[i + 1],
                            round_number=current_round + 1,
                            match_number=(i // 2) + 1,
                            bracket_position=f"WB_R{current_round + 1}M{(i // 2) + 1}",
                        )
                        next_matches.append(match)

            # Send losers to losers bracket
            if losers:
                for i, loser_id in enumerate(losers):
                    # This is simplified - in reality, losers bracket is more complex
                    pass

        return next_matches

    def is_tournament_complete(self, teams: list[TournamentTeam], matches: Sequence[TournamentMatch]) -> bool:
        """Check if double elimination tournament is complete."""
        if not matches:
            return False

        # Tournament is complete when there's a grand final winner
        grand_final = next((m for m in matches if m.bracket_position == "GRAND_FINAL" and m.winner_team_id), None)
        return grand_final is not None

    def get_standings(self, teams: list[TournamentTeam], matches: Sequence[TournamentMatch]) -> list[TournamentTeam]:
        """Get standings for double elimination."""
        # This is a simplified implementation
        # In reality, double elimination standings are complex

        if not matches:
            return teams

        # Find teams that are still in winners bracket vs losers bracket vs eliminated
        active_teams = []
        eliminated_teams = []

        for team in teams:
            team_matches = [m for m in matches if team.id in [m.team1_id, m.team2_id] and m.winner_team_id]
            losses = sum(m.winner_team_id != team.id for m in team_matches)

            if losses >= 2:  # Eliminated in double elimination
                eliminated_teams.append(team)
            else:
                active_teams.append(team)

        # Sort by wins then by losses
        active_teams.sort(key=self.wins_sort, reverse=True)
        eliminated_teams.sort(key=self.wins_sort, reverse=True)

        return active_teams + eliminated_teams

    def wins_sort(self, t: TournamentTeam) -> int:
        """Sort by wins and losses for standings."""
        return t.wins - t.losses
