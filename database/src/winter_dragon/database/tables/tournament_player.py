"""Tournament player database model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship
from winter_dragon.database.extension.model import SQLModel


if TYPE_CHECKING:
    from .tournament import Tournament
    from .tournament_team import TournamentTeam


class PlayerStatus(str, Enum):
    """Player status in tournament."""

    REGISTERED = "registered"
    ACTIVE = "active"
    ELIMINATED = "eliminated"
    WITHDRAWN = "withdrawn"


class TournamentPlayer(SQLModel, table=True):
    """Tournament player registration model."""

    tournament_id: int = Field(foreign_key="tournament.id")
    user_id: int = Field(index=True)
    team_id: int | None = Field(default=None, foreign_key="tournamentteam.id")

    status: PlayerStatus = Field(default=PlayerStatus.REGISTERED)
    registration_date: datetime = Field(default_factory=datetime.utcnow)

    # Player preferences
    preferred_teammates: str | None = Field(default=None, max_length=500)  # Comma-separated user IDs
    avoid_teammates: str | None = Field(default=None, max_length=500)  # Comma-separated user IDs

    # Statistics
    wins: int = Field(default=0, ge=0)
    losses: int = Field(default=0, ge=0)
    draws: int = Field(default=0, ge=0)

    # Relationships
    tournament: Tournament = Relationship(back_populates="players")
    team: TournamentTeam | None = Relationship(back_populates="players")
