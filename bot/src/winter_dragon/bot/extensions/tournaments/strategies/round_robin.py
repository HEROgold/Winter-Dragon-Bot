"""Round robin tournament strategy."""
from __future__ import annotations

from typing import TYPE_CHECKING

from winter_dragon.database.tables import TournamentMatch
from .base import TournamentStrategy

if TYPE_CHECKING:
    from winter_dragon.database.tables import TournamentTeam


class RoundRobinStrategy(TournamentStrategy):
    """Round robin tournament strategy where every team plays every other team."""
    
    async def generate_matches(self, teams: list[TournamentTeam]) -> list[TournamentMatch]:
        """Generate all matches for round robin tournament."""
        if len(teams) < 2:
            return []
        
        matches = []
        match_number = 1
        
        # Generate matches for all team combinations
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                match = TournamentMatch(
                    tournament_id=self.tournament.id,
                    team1_id=teams[i].id,
                    team2_id=teams[j].id,
                    round_number=1,  # All matches are in "round 1" for round robin
                    match_number=match_number,
                    bracket_position=f"RR{match_number}"
                )
                matches.append(match)
                match_number += 1
        
        return matches
    
    async def advance_to_next_round(self, completed_matches: list[TournamentMatch]) -> list[TournamentMatch]:
        """Round robin doesn't have advancing rounds - all matches are generated at start."""
        return []
    
    def is_tournament_complete(self, teams: list[TournamentTeam], matches: list[TournamentMatch]) -> bool:
        """Tournament is complete when all matches are finished."""
        if not matches:
            return False
        
        # All matches should be completed
        return all(match.winner_team_id is not None or match.team1_score == match.team2_score for match in matches)
    
    def get_standings(self, teams: list[TournamentTeam], matches: list[TournamentMatch]) -> list[TournamentTeam]:
        """Get standings based on points (3 for win, 1 for draw, 0 for loss)."""
        team_stats = {team.id: {"team": team, "points": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0} for team in teams}
        
        for match in matches:
            if match.winner_team_id is not None:
                # Completed match
                team1_id, team2_id = match.team1_id, match.team2_id
                team1_score, team2_score = match.team1_score, match.team2_score
                
                # Update goals
                team_stats[team1_id]["goals_for"] += team1_score
                team_stats[team1_id]["goals_against"] += team2_score
                team_stats[team2_id]["goals_for"] += team2_score
                team_stats[team2_id]["goals_against"] += team1_score
                
                if match.winner_team_id == team1_id:
                    # Team 1 wins
                    team_stats[team1_id]["points"] += 3
                    team_stats[team1_id]["wins"] += 1
                    team_stats[team2_id]["losses"] += 1
                elif match.winner_team_id == team2_id:
                    # Team 2 wins
                    team_stats[team2_id]["points"] += 3
                    team_stats[team2_id]["wins"] += 1
                    team_stats[team1_id]["losses"] += 1
            elif match.team1_score == match.team2_score and match.team1_score > 0:
                # Draw
                team1_id, team2_id = match.team1_id, match.team2_id
                team_stats[team1_id]["points"] += 1
                team_stats[team1_id]["draws"] += 1
                team_stats[team2_id]["points"] += 1
                team_stats[team2_id]["draws"] += 1
                
                # Update goals
                team_stats[team1_id]["goals_for"] += match.team1_score
                team_stats[team1_id]["goals_against"] += match.team2_score
                team_stats[team2_id]["goals_for"] += match.team2_score
                team_stats[team2_id]["goals_against"] += match.team1_score
        
        # Sort by points, then by goal difference, then by goals for
        sorted_stats = sorted(
            team_stats.values(),
            key=lambda x: (
                x["points"],
                x["goals_for"] - x["goals_against"],
                x["goals_for"]
            ),
            reverse=True
        )
        
        return [stat["team"] for stat in sorted_stats]