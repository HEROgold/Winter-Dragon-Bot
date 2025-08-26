"""Tournament team database model."""
from __future__ import annotations

from enum import Enum

from sqlmodel import Field, Relationship
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.tournament_match import TeamMatches

from .tournament import Tournament


class TeamStatus(str, Enum):
    """Team status in tournament."""

    ACTIVE = "active"
    ELIMINATED = "eliminated"
    WITHDRAWN = "withdrawn"


class TournamentTeam(SQLModel, table=True):
    """Tournament team model."""

    tournament_id: int = Field(foreign_key=get_foreign_key(Tournament))
    name: str = Field(max_length=100)
    status: TeamStatus = Field(default=TeamStatus.ACTIVE)

    # Relationships
    team_match = Relationship(link_model=TeamMatches)
    tournament: Tournament = Relationship(back_populates="teams")
