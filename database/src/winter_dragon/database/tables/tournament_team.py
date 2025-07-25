"""Tournament team database model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship
from winter_dragon.database.extension.model import SQLModel

if TYPE_CHECKING:
    from .tournament import Tournament
    from .tournament_player import TournamentPlayer
    from .tournament_match import TournamentMatch


class TeamStatus(str, Enum):
    """Team status in tournament."""
    
    ACTIVE = "active"
    ELIMINATED = "eliminated"
    WITHDRAWN = "withdrawn"


class TournamentTeam(SQLModel, table=True):
    """Tournament team model."""
    
    tournament_id: int = Field(foreign_key="tournament.id")
    name: str = Field(max_length=100)
    status: TeamStatus = Field(default=TeamStatus.ACTIVE)
    
    # Discord integration
    text_channel_id: int | None = Field(default=None)
    voice_channel_id: int | None = Field(default=None)
    category_id: int | None = Field(default=None)
    role_id: int | None = Field(default=None)  # For permission management
    
    # Team stats
    wins: int = Field(default=0, ge=0)
    losses: int = Field(default=0, ge=0)
    draws: int = Field(default=0, ge=0)
    points: int = Field(default=0)  # For Swiss/Round Robin tournaments
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    captain_id: int | None = Field(default=None)  # Team captain user ID
    
    # Relationships
    tournament: Tournament = Relationship(back_populates="teams")
    players: list[TournamentPlayer] = Relationship(back_populates="team")
    home_matches: list[TournamentMatch] = Relationship(
        back_populates="team1",
        sa_relationship_kwargs={"foreign_keys": "TournamentMatch.team1_id"}
    )
    away_matches: list[TournamentMatch] = Relationship(
        back_populates="team2", 
        sa_relationship_kwargs={"foreign_keys": "TournamentMatch.team2_id"}
    )