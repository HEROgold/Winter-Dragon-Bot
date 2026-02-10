"""Database models and data classes for the tournament extension."""

from dataclasses import dataclass, field


@dataclass
class TournamentVote:
    """Tracks voting and participation for a tournament."""

    # Game voting
    votes: dict[int, str] = field(default_factory=dict)  # user_id -> game_name
    vote_counts: dict[str, int] = field(default_factory=dict)  # game_name -> count

    # Format voting
    format_votes: dict[int, str] = field(default_factory=dict)  # user_id -> format
    format_counts: dict[str, int] = field(default_factory=dict)  # format -> count

    # Participants
    participants: list[int] = field(default_factory=list)  # List of user IDs

    # Status
    voting_concluded: bool = False
    tournament_started: bool = False
    winning_game: str | None = None
    winning_format: str | None = None
