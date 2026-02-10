"""Matchmaking system for tournament bracket generation.

This module implements a sophisticated matchmaking algorithm that:
- Balances teams based on player skill ratings
- Considers player synergy (performance with teammates)
- Avoids placing high-synergy players together for competitive balance
- Takes into account game-specific player performance
- Supports multiple bracket formats (1v1, 2v2, 3v3, FFA, etc.)
"""

from __future__ import annotations

import itertools
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from herogold.log import LoggerMixin
from sqlmodel import Session, select

from winter_dragon.database.constants import session as db_session
from winter_dragon.database.tables.game import Games
from winter_dragon.database.tables.matchmaking.game_match import GameMatch
from winter_dragon.database.tables.matchmaking.match_player import MatchPlayer
from winter_dragon.database.tables.matchmaking.match_team import MatchTeam
from winter_dragon.database.tables.matchmaking.player_game_stats import PlayerGameStats
from winter_dragon.database.tables.matchmaking.player_synergy import PlayerSynergy
from winter_dragon.database.tables.matchmaking.team_composition import TeamComposition
from winter_dragon.database.tables.matchmaking.team_composition_player import TeamCompositionPlayer
from winter_dragon.database.tables.user import Users


@dataclass
class PlayerProfile:
    """Player profile for matchmaking calculations."""

    user_id: int
    skill_rating: float = 1000.0
    win_rate: float = 0.0
    avg_score: float = 0.0
    total_matches: int = 0


@dataclass
class TeamCandidate:
    """Candidate team composition for evaluation."""

    players: list[PlayerProfile]
    avg_skill: float = 0.0
    synergy_penalty: float = 0.0
    balance_score: float = 0.0

    def __post_init__(self):
        """Calculate average skill on initialization."""
        if self.players:
            self.avg_skill = sum(p.skill_rating for p in self.players) / len(self.players)


class MatchmakingSystem(LoggerMixin):
    """Main matchmaking system for balanced team generation."""

    def __init__(self, session: Session | None = None) -> None:
        """Initialize matchmaking system.

        Args:
        ----
            session: Database session. Uses default if None.

        """
        self.session = session or db_session
        self.logger.info("MatchmakingSystem initialized")

    def create_balanced_teams(
        self,
        game_name: str,
        player_ids: list[int],
        bracket_format: str = "2v2",
        avoid_synergy: bool = True,
    ) -> list[list[int]]:
        """Create balanced teams for a match.

        Args:
        ----
            game_name: Name of the game
            player_ids: List of player user IDs
            bracket_format: Format like "1v1", "2v2", "3v3", "ffa"
            avoid_synergy: Whether to avoid pairing high-synergy players

        Returns:
        -------
            List of teams, where each team is a list of user IDs

        """
        self.logger.info(
            f"Creating balanced teams for {game_name}: {len(player_ids)} players, "
            f"format={bracket_format}, avoid_synergy={avoid_synergy}"
        )

        # Parse bracket format
        team_size, num_teams = self._parse_bracket_format(bracket_format, len(player_ids))

        if len(player_ids) != team_size * num_teams:
            msg = f"Player count {len(player_ids)} doesn't match format {bracket_format}"
            raise ValueError(msg)

        # Get game
        game = Games.fetch_game_by_name(game_name)
        self.logger.debug(f"Game fetched: {game.name} (ID: {game.id})")

        # Load player profiles
        profiles = self._load_player_profiles(game.id, player_ids)
        self.logger.debug(f"Loaded {len(profiles)} player profiles")

        # Load synergy data
        synergy_map = self._load_synergy_data(game.id, player_ids) if avoid_synergy else {}

        # Generate and evaluate team combinations
        best_teams = self._find_best_team_split(
            profiles,
            team_size,
            num_teams,
            synergy_map,
        )

        result = [[p.user_id for p in team.players] for team in best_teams]
        self.logger.info(f"Successfully created {len(result)} balanced teams")
        self.logger.debug(f"Team composition: {result}")
        return result

    def record_match_result(
        self,
        game_name: str,
        teams: list[list[int]],
        winning_team_idx: int,
        bracket_format: str,
        individual_scores: dict[int, int] | None = None,
        team_scores: list[int] | None = None,
        duration_seconds: int | None = None,
    ) -> GameMatch:
        """Record match results and update statistics.

        Args:
        ----
            game_name: Name of the game
            teams: List of teams (each team is list of user IDs)
            winning_team_idx: Index of winning team (0-based)
            bracket_format: Format like "2v2"
            individual_scores: Optional dict mapping user_id to score
            team_scores: Optional list of team scores
            duration_seconds: Optional match duration

        Returns:
        -------
            Created GameMatch instance

        """
        self.logger.info(
            f"Recording match result for {game_name}: {len(teams)} teams, "
            f"winner=team_{winning_team_idx}, format={bracket_format}"
        )

        game = Games.fetch_game_by_name(game_name)
        individual_scores = individual_scores or {}
        team_scores = team_scores or []

        # Create match record
        match = GameMatch(
            game_id=game.id,
            match_date=datetime.now(),
            duration_seconds=duration_seconds,
            winning_team_id=winning_team_idx + 1,
            bracket_format=bracket_format,
        )
        match.add(self.session)
        self.session.commit()

        # Record team results
        for team_idx, team_players in enumerate(teams):
            team_won = team_idx == winning_team_idx
            team_score = team_scores[team_idx] if team_idx < len(team_scores) else None

            match_team = MatchTeam(
                match_id=match.id,
                team_number=team_idx + 1,
                team_score=team_score,
                won=team_won,
            )
            match_team.add(self.session)

        # Record player results
        for team_idx, team_players in enumerate(teams):
            team_won = team_idx == winning_team_idx
            for user_id in team_players:
                match_player = MatchPlayer(
                    match_id=match.id,
                    user_id=user_id,
                    team_number=team_idx + 1,
                    individual_score=individual_scores.get(user_id),
                    won=team_won,
                )
                match_player.add(self.session)

        self.session.commit()

        # Update aggregated statistics
        self._update_player_stats(game.id, teams, winning_team_idx, individual_scores)
        self._update_synergy_stats(game.id, teams, winning_team_idx)
        self._update_team_composition_stats(game.id, teams, winning_team_idx, team_scores)

        return match

    def _parse_bracket_format(self, bracket_format: str, total_players: int) -> tuple[int, int]:
        """Parse bracket format string.

        Args:
        ----
            bracket_format: Format like "2v2", "1v1", "3v3", "ffa"
            total_players: Total number of players

        Returns:
        -------
            Tuple of (team_size, num_teams)

        """
        if bracket_format.lower() == "ffa":
            return 1, total_players

        if "v" in bracket_format:
            parts = bracket_format.lower().split("v")
            team_size = int(parts[0])
            num_teams = int(parts[1]) if len(parts) > 1 else 2
            return team_size, num_teams

        msg = f"Invalid bracket format: {bracket_format}"
        raise ValueError(msg)

    def _load_player_profiles(self, game_id: int, player_ids: list[int]) -> list[PlayerProfile]:
        """Load player profiles from database.

        Args:
        ----
            game_id: Game ID
            player_ids: List of player user IDs

        Returns:
        -------
            List of PlayerProfile objects

        """
        profiles = []

        for user_id in player_ids:
            # Get or create stats
            stats = self.session.exec(
                select(PlayerGameStats).where(PlayerGameStats.user_id == user_id).where(PlayerGameStats.game_id == game_id)
            ).first()

            if stats:
                profile = PlayerProfile(
                    user_id=user_id,
                    skill_rating=stats.skill_rating,
                    win_rate=stats.win_rate,
                    avg_score=stats.avg_score,
                    total_matches=stats.total_matches,
                )
            else:
                # New player with default values
                profile = PlayerProfile(user_id=user_id)

            profiles.append(profile)

        return profiles

    def _load_synergy_data(
        self,
        game_id: int,
        player_ids: list[int],
    ) -> dict[tuple[int, int], float]:
        """Load synergy data between players.

        Args:
        ----
            game_id: Game ID
            player_ids: List of player user IDs

        Returns:
        -------
            Dict mapping (player1_id, player2_id) to synergy score

        """
        synergy_map = {}

        # Query all synergy pairs for these players
        synergies = self.session.exec(
            select(PlayerSynergy)
            .where(PlayerSynergy.game_id == game_id)
            .where(PlayerSynergy.player1_id in (player_ids))
            .where(PlayerSynergy.player2_id in (player_ids))
        ).all()

        for synergy in synergies:
            # Store synergy score (higher = better teammates)
            key = tuple(sorted([synergy.player1_id, synergy.player2_id]))
            synergy_map[key] = synergy.teammate_synergy

        return synergy_map

    def _find_best_team_split(
        self,
        profiles: list[PlayerProfile],
        team_size: int,
        num_teams: int,
        synergy_map: dict[tuple[int, int], float],
    ) -> list[TeamCandidate]:
        """Find the best way to split players into teams.

        Uses iterative approach with random sampling for large groups.

        Args:
        ----
            profiles: List of player profiles
            team_size: Number of players per team
            num_teams: Number of teams
            synergy_map: Synergy data between players

        Returns:
        -------
            List of TeamCandidate objects representing optimal teams

        """
        # For small groups, try all combinations
        if len(profiles) <= 8:
            return self._exhaustive_team_search(profiles, team_size, num_teams, synergy_map)

        # For large groups, use iterative improvement
        return self._iterative_team_search(profiles, team_size, num_teams, synergy_map)

    def _exhaustive_team_search(
        self,
        profiles: list[PlayerProfile],
        team_size: int,
        num_teams: int,
        synergy_map: dict[tuple[int, int], float],
    ) -> list[TeamCandidate]:
        """Exhaustive search for small player counts.

        Args:
        ----
            profiles: List of player profiles
            team_size: Number of players per team
            num_teams: Number of teams
            synergy_map: Synergy data between players

        Returns:
        -------
            List of TeamCandidate objects representing optimal teams

        """
        best_teams = None
        best_score = float("inf")

        # Generate all possible team splits
        for team_combo in self._generate_team_combinations(profiles, team_size, num_teams):
            teams = [TeamCandidate(players=team) for team in team_combo]
            score = self._evaluate_team_balance(teams, synergy_map)

            if score < best_score:
                best_score = score
                best_teams = teams

        return best_teams or []

    def _iterative_team_search(
        self,
        profiles: list[PlayerProfile],
        team_size: int,
        num_teams: int,
        synergy_map: dict[tuple[int, int], float],
        iterations: int = 1000,
    ) -> list[TeamCandidate]:
        """Iterative improvement search for large player counts.

        Args:
        ----
            profiles: List of player profiles
            team_size: Number of players per team
            num_teams: Number of teams
            synergy_map: Synergy data between players
            iterations: Number of random attempts

        Returns:
        -------
            List of TeamCandidate objects representing optimal teams

        """
        best_teams = None
        best_score = float("inf")

        for _ in range(iterations):
            # Random shuffle and split
            shuffled = profiles.copy()
            random.shuffle(shuffled)

            teams = []
            for i in range(num_teams):
                team_players = shuffled[i * team_size : (i + 1) * team_size]
                teams.append(TeamCandidate(players=team_players))

            score = self._evaluate_team_balance(teams, synergy_map)

            if score < best_score:
                best_score = score
                best_teams = teams

        return best_teams or []

    def _generate_team_combinations(
        self,
        profiles: list[PlayerProfile],
        team_size: int,
        num_teams: int,
    ) -> list[list[list[PlayerProfile]]]:
        """Generate all possible team combinations.

        Args:
        ----
            profiles: List of player profiles
            team_size: Number of players per team
            num_teams: Number of teams

        Yields:
        ------
            Lists of team combinations

        """
        if num_teams == 2:
            # Special case for 2 teams - more efficient
            for team1 in itertools.combinations(profiles, team_size):
                team2 = [p for p in profiles if p not in team1]
                yield [list(team1), team2]
        else:
            # General case - recursive split
            def split_teams(remaining, teams_left):
                if teams_left == 1:
                    yield [remaining]
                    return

                for team in itertools.combinations(remaining, team_size):
                    rest = [p for p in remaining if p not in team]
                    for sub_split in split_teams(rest, teams_left - 1):
                        yield [list(team), *sub_split]

            yield from split_teams(profiles, num_teams)

    def _evaluate_team_balance(
        self,
        teams: list[TeamCandidate],
        synergy_map: dict[tuple[int, int], float],
        skill_weight: float = 1.0,
        synergy_weight: float = 0.5,
    ) -> float:
        """Evaluate how balanced a team split is.

        Lower score = better balance

        Args:
        ----
            teams: List of team candidates
            synergy_map: Synergy data between players
            skill_weight: Weight for skill imbalance
            synergy_weight: Weight for synergy penalty

        Returns:
        -------
            Balance score (lower is better)

        """
        # Calculate skill variance between teams
        avg_skills = [team.avg_skill for team in teams]
        skill_variance = sum((s - sum(avg_skills) / len(avg_skills)) ** 2 for s in avg_skills)

        # Calculate synergy penalties (we want to AVOID high synergy pairs)
        total_synergy_penalty = 0.0
        for team in teams:
            team_synergy = 0.0
            for i, p1 in enumerate(team.players):
                for p2 in team.players[i + 1 :]:
                    key = tuple(sorted([p1.user_id, p2.user_id]))
                    # Penalize high synergy (good teammates)
                    synergy = synergy_map.get(key, 0.0)
                    team_synergy += synergy
            total_synergy_penalty += team_synergy

        # Combined score
        return (skill_weight * skill_variance) + (synergy_weight * total_synergy_penalty)

    def _update_player_stats(
        self,
        game_id: int,
        teams: list[list[int]],
        winning_team_idx: int,
        individual_scores: dict[int, int],
    ) -> None:
        """Update player statistics after a match.

        Args:
        ----
            game_id: Game ID
            teams: List of teams (user IDs)
            winning_team_idx: Index of winning team
            individual_scores: Individual player scores

        """
        for team_idx, team_players in enumerate(teams):
            team_won = team_idx == winning_team_idx

            for user_id in team_players:
                # Get or create stats
                stats = self.session.exec(
                    select(PlayerGameStats).where(PlayerGameStats.user_id == user_id).where(PlayerGameStats.game_id == game_id)
                ).first()

                if not stats:
                    stats = PlayerGameStats(user_id=user_id, game_id=game_id)
                    stats.add(self.session)

                # Update counts
                stats.total_matches += 1
                if team_won:
                    stats.total_wins += 1
                else:
                    stats.total_losses += 1

                # Update win rate
                stats.win_rate = stats.total_wins / stats.total_matches if stats.total_matches > 0 else 0.0

                # Update average score
                if user_id in individual_scores:
                    old_total = stats.avg_score * (stats.total_matches - 1)
                    stats.avg_score = (old_total + individual_scores[user_id]) / stats.total_matches

                # Update skill rating (simple ELO-like adjustment)
                k_factor = 32
                expected_score = 0.5  # Could be refined with opponent ratings
                actual_score = 1.0 if team_won else 0.0
                stats.skill_rating += k_factor * (actual_score - expected_score)

                stats.update(self.session)

        self.session.commit()

    def _update_synergy_stats(
        self,
        game_id: int,
        teams: list[list[int]],
        winning_team_idx: int,
    ) -> None:
        """Update player synergy statistics.

        Args:
        ----
            game_id: Game ID
            teams: List of teams (user IDs)
            winning_team_idx: Index of winning team

        """
        # Update teammate synergies
        for team_idx, team_players in enumerate(teams):
            team_won = team_idx == winning_team_idx

            # Update all pairs within the team
            for i, player1_id in enumerate(team_players):
                for player2_id in team_players[i + 1 :]:
                    # Ensure consistent ordering
                    p1, p2 = sorted([player1_id, player2_id])

                    synergy = self.session.exec(
                        select(PlayerSynergy)
                        .where(PlayerSynergy.player1_id == p1)
                        .where(PlayerSynergy.player2_id == p2)
                        .where(PlayerSynergy.game_id == game_id)
                    ).first()

                    if not synergy:
                        synergy = PlayerSynergy(
                            player1_id=p1,
                            player2_id=p2,
                            game_id=game_id,
                        )
                        synergy.add(self.session)

                    synergy.matches_as_teammates += 1
                    if team_won:
                        synergy.wins_as_teammates += 1

                    synergy.teammate_synergy = (
                        synergy.wins_as_teammates / synergy.matches_as_teammates if synergy.matches_as_teammates > 0 else 0.0
                    )

                    synergy.update(self.session)

        # Update opponent rivalries (cross-team)
        for team1_idx, team1_players in enumerate(teams):
            for team2_idx, team2_players in enumerate(teams):
                if team1_idx >= team2_idx:
                    continue  # Skip same team and avoid duplicates

                team1_won = team1_idx == winning_team_idx

                for player1_id in team1_players:
                    for player2_id in team2_players:
                        # Ensure consistent ordering
                        p1, p2 = sorted([player1_id, player2_id])

                        synergy = self.session.exec(
                            select(PlayerSynergy)
                            .where(PlayerSynergy.player1_id == p1)
                            .where(PlayerSynergy.player2_id == p2)
                            .where(PlayerSynergy.game_id == game_id)
                        ).first()

                        if not synergy:
                            synergy = PlayerSynergy(
                                player1_id=p1,
                                player2_id=p2,
                                game_id=game_id,
                            )
                            synergy.add(self.session)

                        synergy.matches_as_opponents += 1

                        # Track wins (considering ordered IDs)
                        if (player1_id == p1 and team1_won) or (player2_id == p1 and not team1_won):
                            synergy.player1_wins_vs_player2 += 1

                        synergy.rivalry_factor = (
                            synergy.player1_wins_vs_player2 / synergy.matches_as_opponents
                            if synergy.matches_as_opponents > 0
                            else 0.0
                        )

                        synergy.update(self.session)

        self.session.commit()

    def _update_team_composition_stats(
        self,
        game_id: int,
        teams: list[list[int]],
        winning_team_idx: int,
        team_scores: list[int],
    ) -> None:
        """Update team composition statistics.

        Args:
        ----
            game_id: Game ID
            teams: List of teams (user IDs)
            winning_team_idx: Index of winning team
            team_scores: Team scores

        """
        for team_idx, team_players in enumerate(teams):
            team_won = team_idx == winning_team_idx
            team_score = team_scores[team_idx] if team_idx < len(team_scores) else 0

            # Create composition key (sorted player IDs)
            sorted_player_ids = sorted(team_players)

            # Try to find existing composition with these exact players
            # Query by joining with TeamCompositionPlayer
            existing_compositions = self.session.exec(select(TeamComposition).where(TeamComposition.game_id == game_id)).all()

            composition = None
            for comp in existing_compositions:
                # Get players for this composition
                comp_players = self.session.exec(
                    select(TeamCompositionPlayer.user_id).where(TeamCompositionPlayer.composition_id == comp.id)
                ).all()

                if sorted(comp_players) == sorted_player_ids:
                    composition = comp
                    break

            if not composition:
                # Create new composition
                composition = TeamComposition(
                    game_id=game_id,
                )
                composition.add(self.session)
                self.session.commit()

                # Add players to composition
                for user_id in team_players:
                    comp_player = TeamCompositionPlayer(
                        composition_id=composition.id,
                        user_id=user_id,
                    )
                    comp_player.add(self.session)
                self.session.commit()

            composition.times_played += 1
            if team_won:
                composition.wins += 1
            else:
                composition.losses += 1

            composition.win_rate = composition.wins / composition.times_played if composition.times_played > 0 else 0.0

            # Update average score
            old_total = composition.avg_team_score * (composition.times_played - 1)
            composition.avg_team_score = (old_total + team_score) / composition.times_played

            composition.update(self.session)

        self.session.commit()

    # ========== Example Data & Debugging Methods ==========

    def generate_example_data(self, num_players: int = 10, num_matches: int = 50) -> None:
        """Generate example data for testing.

        Args:
        ----
            num_players: Number of players to create
            num_matches: Number of matches to simulate

        """
        # Create example game
        game = Games.fetch_game_by_name("League of Legends")

        # Create example users (if they don't exist)
        user_ids = []
        for i in range(1, num_players + 1):
            user_id = 100000 + i
            user_ids.append(user_id)

            # Check if user exists
            user = self.session.exec(select(Users).where(Users.id == user_id)).first()
            if not user:
                user = Users(id=user_id)
                user.add(self.session)

        self.session.commit()

        # Simulate matches
        for match_num in range(num_matches):
            # Random team composition (2v2 or 3v3)
            bracket_format = random.choice(["2v2", "3v3"])
            team_size = int(bracket_format[0])

            # Select random players
            selected_players = random.sample(user_ids, team_size * 2)

            # Create balanced teams
            try:
                teams = self.create_balanced_teams(
                    game_name=game.name,
                    player_ids=selected_players,
                    bracket_format=bracket_format,
                    avoid_synergy=(match_num > 10),  # Start avoiding synergy after initial matches
                )
            except Exception:
                # Fallback to random teams
                teams = [
                    selected_players[:team_size],
                    selected_players[team_size:],
                ]

            # Random winner
            winning_team = random.randint(0, 1)

            # Random scores
            individual_scores = {player_id: random.randint(100, 500) for player_id in selected_players}
            team_scores = [
                sum(individual_scores[p] for p in teams[0]),
                sum(individual_scores[p] for p in teams[1]),
            ]

            # Record match
            self.record_match_result(
                game_name=game.name,
                teams=teams,
                winning_team_idx=winning_team,
                bracket_format=bracket_format,
                individual_scores=individual_scores,
                team_scores=team_scores,
                duration_seconds=random.randint(600, 3600),
            )

    def print_player_stats(self, game_name: str, limit: int = 10) -> None:
        """Print player statistics for debugging.

        Args:
        ----
            game_name: Name of the game
            limit: Maximum number of players to show

        """
        game = Games.fetch_game_by_name(game_name)

        stats_list = self.session.exec(
            select(PlayerGameStats)
            .where(PlayerGameStats.game_id == game.id)
            .order_by(PlayerGameStats.skill_rating.desc())
            .limit(limit)
        ).all()

        for _stats in stats_list:
            pass

    def print_synergy_data(self, game_name: str, limit: int = 15) -> None:
        """Print player synergy data for debugging.

        Args:
        ----
            game_name: Name of the game
            limit: Maximum number of pairs to show

        """
        game = Games.fetch_game_by_name(game_name)

        synergies = self.session.exec(
            select(PlayerSynergy)
            .where(PlayerSynergy.game_id == game.id)
            .where(PlayerSynergy.matches_as_teammates > 0)
            .order_by(PlayerSynergy.teammate_synergy.desc())
            .limit(limit)
        ).all()

        for _synergy in synergies:
            pass

    def print_match_history(self, game_name: str, limit: int = 10) -> None:
        """Print recent match history for debugging.

        Args:
        ----
            game_name: Name of the game
            limit: Maximum number of matches to show

        """
        game = Games.fetch_game_by_name(game_name)

        matches = self.session.exec(
            select(GameMatch).where(GameMatch.game_id == game.id).order_by(GameMatch.match_date.desc()).limit(limit)
        ).all()

        for match in matches:
            players = self.session.exec(select(MatchPlayer).where(MatchPlayer.match_id == match.id)).all()

            teams = defaultdict(list)
            for player in players:
                teams[player.team_number].append(f"{player.user_id}{'*' if player.won else ''}")

            for _team_num, _team_players in sorted(teams.items()):
                pass

    def verify_data_integrity(self) -> dict[str, int | str]:
        """Verify data integrity for debugging.

        Returns
        -------
            Dictionary with verification results

        """
        results = {}

        # Count records
        results["total_matches"] = len(self.session.exec(select(GameMatch)).all())
        results["total_players_in_matches"] = len(self.session.exec(select(MatchPlayer)).all())
        results["total_teams"] = len(self.session.exec(select(MatchTeam)).all())
        results["total_player_stats"] = len(self.session.exec(select(PlayerGameStats)).all())
        results["total_synergies"] = len(self.session.exec(select(PlayerSynergy)).all())
        results["total_compositions"] = len(self.session.exec(select(TeamComposition)).all())

        # Check for orphaned records
        match_players = self.session.exec(select(MatchPlayer)).all()
        match_ids = {m.id for m in self.session.exec(select(GameMatch)).all()}
        orphaned_players = sum(1 for mp in match_players if mp.match_id not in match_ids)
        results["orphaned_players"] = orphaned_players

        results["status"] = "OK" if orphaned_players == 0 else "WARNINGS"

        return results


# Example usage and testing
if __name__ == "__main__":
    # Initialize system
    mm = MatchmakingSystem()

    # Generate example data
    mm.generate_example_data(num_players=12, num_matches=100)

    # Print statistics
    mm.print_player_stats("League of Legends")
    mm.print_synergy_data("League of Legends")
    mm.print_match_history("League of Legends")

    # Verify integrity
    integrity = mm.verify_data_integrity()
    for _key, _value in integrity.items():
        pass

    # Test matchmaking

    test_players = [100001, 100002, 100003, 100004, 100005, 100006]
    teams = mm.create_balanced_teams(
        game_name="League of Legends",
        player_ids=test_players,
        bracket_format="3v3",
        avoid_synergy=True,
    )

    for _i, _team in enumerate(teams, 1):
        pass
