"""Single elimination tournament strategy."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from winter_dragon.database.tables import TournamentMatch
from .base import TournamentStrategy

if TYPE_CHECKING:
    from winter_dragon.database.tables import TournamentTeam


class SingleEliminationStrategy(TournamentStrategy):
    """Single elimination tournament strategy."""
    
    def validate_team_count(self, team_count: int) -> bool:
        """Validate team count (must be power of 2 for clean bracket)."""
        return team_count >= 2 and (team_count & (team_count - 1)) == 0
    
    async def generate_matches(self, teams: list[TournamentTeam]) -> list[TournamentMatch]:
        """Generate first round matches for single elimination."""
        if len(teams) < 2:
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
                    bracket_position=f"R1M{(i // 2) + 1}"
                )
                matches.append(match)
        
        return matches
    
    async def advance_to_next_round(self, completed_matches: list[TournamentMatch]) -> list[TournamentMatch]:
        """Advance to next round based on completed matches."""
        if not completed_matches:
            return []
        
        current_round = completed_matches[0].round_number
        winners = []
        
        for match in completed_matches:
            if match.round_number == current_round and match.winner_team_id:
                winners.append(match.winner_team_id)
        
        if len(winners) < 2:
            return []
        
        next_round_matches = []
        next_round = current_round + 1
        
        for i in range(0, len(winners), 2):
            if i + 1 < len(winners):
                match = TournamentMatch(
                    tournament_id=self.tournament.id,
                    team1_id=winners[i],
                    team2_id=winners[i + 1],
                    round_number=next_round,
                    match_number=(i // 2) + 1,
                    bracket_position=f"R{next_round}M{(i // 2) + 1}"
                )
                next_round_matches.append(match)
        
        return next_round_matches
    
    def is_tournament_complete(self, teams: list[TournamentTeam], matches: list[TournamentMatch]) -> bool:
        """Check if tournament is complete (only one team remaining)."""
        if not matches:
            return False
        
        # Find the highest round with completed matches
        completed_matches = [m for m in matches if m.winner_team_id is not None]
        if not completed_matches:
            return False
        
        max_round = max(m.round_number for m in completed_matches)
        final_round_matches = [m for m in completed_matches if m.round_number == max_round]
        
        # Tournament is complete if there's only one match in the final round and it's completed
        return len(final_round_matches) == 1
    
    def get_standings(self, teams: list[TournamentTeam], matches: list[TournamentMatch]) -> list[TournamentTeam]:
        """Get standings for single elimination (winner first, then by elimination round)."""
        if not matches:
            return teams
        
        # Find eliminated teams by round
        eliminated_by_round = {}
        winner = None
        
        for match in matches:
            if match.winner_team_id:
                loser_id = match.team1_id if match.winner_team_id == match.team2_id else match.team2_id
                eliminated_by_round[loser_id] = match.round_number
                
                # Check if this is the final
                if self.is_tournament_complete(teams, matches):
                    winner = match.winner_team_id
        
        standings = []
        
        # Add winner first
        if winner:
            winner_team = next((t for t in teams if t.id == winner), None)
            if winner_team:
                standings.append(winner_team)
        
        # Add eliminated teams by reverse round order (later elimination = higher placement)
        for round_num in sorted(eliminated_by_round.keys(), reverse=True):
            team_ids = [tid for tid, r in eliminated_by_round.items() if r == round_num]
            for team_id in team_ids:
                team = next((t for t in teams if t.id == team_id), None)
                if team and team not in standings:
                    standings.append(team)
        
        # Add remaining teams that haven't been eliminated
        for team in teams:
            if team not in standings:
                standings.append(team)
        
        return standings