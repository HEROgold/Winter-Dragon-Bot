"""Tournament spectator database model."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship
from winter_dragon.database.extension.model import SQLModel


if TYPE_CHECKING:
    from .tournament import Tournament


class TournamentSpectator(SQLModel, table=True):
    """Tournament spectator model."""

    tournament_id: int = Field(foreign_key="tournament.id")
    user_id: int = Field(index=True)

    # Spectator preferences
    notifications_enabled: bool = Field(default=True)
    favorite_teams: str | None = Field(default=None, max_length=500)  # Comma-separated team IDs

    # Metadata
    joined_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    tournament: Tournament = Relationship(back_populates="spectators")
