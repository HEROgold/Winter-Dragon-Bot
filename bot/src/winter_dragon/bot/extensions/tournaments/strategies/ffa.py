"""Free-for-all tournament strategy."""
from __future__ import annotations

from typing import TYPE_CHECKING

from winter_dragon.database.tables import TournamentMatch
from .base import TournamentStrategy

if TYPE_CHECKING:
    from winter_dragon.database.tables import TournamentTeam


class FFAStrategy(TournamentStrategy):
    """Free-for-all tournament strategy where teams compete in multiple rounds."""
    
    async def generate_matches(self, teams: list[TournamentTeam]) -> list[TournamentMatch]:
        """Generate FFA matches - teams compete in groups."""
        if len(teams) < 3:
            return []
        
        matches = []
        
        # For FFA, we can create multiple "matches" where teams compete
        # This is a simplified implementation - in reality FFA might have different rules
        
        # Create round 1 matches with groups of teams
        group_size = min(8, len(teams))  # Max 8 teams per FFA match
        
        for i in range(0, len(teams), group_size):
            group_teams = teams[i:i + group_size]
            if len(group_teams) >= 3:  # Need at least 3 for FFA
                # Create a match representing this FFA group
                # We'll use team1_id and team2_id for the first two teams
                # In reality, you'd need a different structure for FFA
                match = TournamentMatch(
                    tournament_id=self.tournament.id,
                    team1_id=group_teams[0].id,
                    team2_id=group_teams[1].id,
                    round_number=1,
                    match_number=(i // group_size) + 1,
                    bracket_position=f"FFA_R1G{(i // group_size) + 1}",
                    notes=f"FFA Group with teams: {', '.join(t.name for t in group_teams)}"
                )
                matches.append(match)
        
        return matches
    
    async def advance_to_next_round(self, completed_matches: list[TournamentMatch]) -> list[TournamentMatch]:
        """Advance to next round - top performers from each group."""
        if not completed_matches:
            return []
        
        # In FFA, advancement is based on placement in each group
        # This is a simplified implementation
        current_round = max(m.round_number for m in completed_matches)
        
        # Get winners from current round
        winners = []
        for match in completed_matches:
            if match.round_number == current_round and match.winner_team_id:
                winners.append(match.winner_team_id)
        
        if len(winners) < 3:
            return []
        
        # Create next round FFA match
        group_size = min(8, len(winners))
        next_matches = []
        
        for i in range(0, len(winners), group_size):
            group_winners = winners[i:i + group_size]
            if len(group_winners) >= 3:
                match = TournamentMatch(
                    tournament_id=self.tournament.id,
                    team1_id=group_winners[0],
                    team2_id=group_winners[1],
                    round_number=current_round + 1,
                    match_number=(i // group_size) + 1,
                    bracket_position=f"FFA_R{current_round + 1}G{(i // group_size) + 1}",
                    notes=f"FFA Group with {len(group_winners)} teams"
                )
                next_matches.append(match)
        
        return next_matches
    
    def is_tournament_complete(self, teams: list[TournamentTeam], matches: list[TournamentMatch]) -> bool:
        """Tournament is complete when there's a final winner."""
        if not matches:
            return False
        
        # Find the highest round with completed matches
        completed_matches = [m for m in matches if m.winner_team_id is not None]
        if not completed_matches:
            return False
        
        max_round = max(m.round_number for m in completed_matches)
        final_round_matches = [m for m in completed_matches if m.round_number == max_round]
        
        # Tournament is complete if there's only one match in the final round
        return len(final_round_matches) == 1
    
    def get_standings(self, teams: list[TournamentTeam], matches: list[TournamentMatch]) -> list[TournamentTeam]:
        """Get standings for FFA tournament."""
        if not matches:
            return teams
        
        # In FFA, standings are based on placement in matches
        team_scores = {team.id: {"team": team, "total_score": 0, "rounds_played": 0} for team in teams}
        
        for match in matches:
            if match.winner_team_id:
                # Winner gets points based on round
                team_scores[match.winner_team_id]["total_score"] += match.round_number * 3
                team_scores[match.winner_team_id]["rounds_played"] += 1
                
                # Other teams in the match get participation points
                # This is simplified since we can't track all FFA participants easily
                for team_id in [match.team1_id, match.team2_id]:
                    if team_id != match.winner_team_id:
                        team_scores[team_id]["total_score"] += 1
                        team_scores[team_id]["rounds_played"] += 1
        
        # Sort by total score, then by rounds played
        sorted_teams = sorted(
            team_scores.values(),
            key=lambda x: (x["total_score"], x["rounds_played"]),
            reverse=True
        )
        
        return [score["team"] for score in sorted_teams]