"""Tournament match database model."""
from __future__ import annotations

from enum import Enum

from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.tournament_team import TournamentTeam

from .tournament import Tournament


class MatchStatus(str, Enum):
    """Match status enumeration."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class TournamentMatch(SQLModel, table=True):
    """Tournament match model."""

    tournament_id: int = Field(primary_key=True, foreign_key=get_foreign_key(Tournament))
    match_id: int = Field(primary_key=True, index=True)


class TeamMatches(SQLModel, table=True):
    """Team matches model."""

    team_id: int = Field(primary_key=True, foreign_key=get_foreign_key(TournamentTeam))
    match_id: int = Field(primary_key=True, foreign_key=get_foreign_key(TournamentMatch))
