"""Tournament match database model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship
from winter_dragon.database.extension.model import SQLModel

if TYPE_CHECKING:
    from .tournament import Tournament
    from .tournament_team import TournamentTeam


class MatchStatus(str, Enum):
    """Match status enumeration."""
    
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class TournamentMatch(SQLModel, table=True):
    """Tournament match model."""
    
    tournament_id: int = Field(foreign_key="tournament.id")
    
    # Teams
    team1_id: int = Field(foreign_key="tournamentteam.id")
    team2_id: int = Field(foreign_key="tournamentteam.id")
    
    # Match details
    round_number: int = Field(ge=1)
    match_number: int = Field(ge=1)  # Match number within the round
    bracket_position: str | None = Field(default=None, max_length=50)  # For elimination brackets
    
    # Scores
    team1_score: int = Field(default=0, ge=0)
    team2_score: int = Field(default=0, ge=0)
    winner_team_id: int | None = Field(default=None)
    
    # Status and timing
    status: MatchStatus = Field(default=MatchStatus.SCHEDULED)
    scheduled_time: datetime | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    
    # Discord integration
    thread_id: int | None = Field(default=None)  # Match discussion thread
    
    # Additional data
    notes: str | None = Field(default=None, max_length=500)
    reported_by_id: int | None = Field(default=None)  # User who reported the result
    
    # Relationships
    tournament: Tournament = Relationship(back_populates="matches")
    team1: TournamentTeam = Relationship(
        back_populates="home_matches",
        sa_relationship_kwargs={"foreign_keys": "[TournamentMatch.team1_id]"}
    )
    team2: TournamentTeam = Relationship(
        back_populates="away_matches",
        sa_relationship_kwargs={"foreign_keys": "[TournamentMatch.team2_id]"}
    )