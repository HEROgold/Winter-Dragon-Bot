"""GameMatch table - stores information about completed matches."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key


if TYPE_CHECKING:
    from wd_db.tables.game import Games
    from wd_db.tables.matchmaking.match_player import MatchPlayer
    from wd_db.tables.matchmaking.match_team import MatchTeam
else:
    from wd_db.tables import Games


class GameMatch(SQLModel, table=True):
    """Represents a completed match/game session.

    Stores core match information in 6NF - only facts about the match itself.
    """

    game_id: int = Field(foreign_key=get_foreign_key(Games), index=True)
    match_date: datetime = Field(default_factory=datetime.now, index=True)
    duration_seconds: int | None = Field(default=None)
    winning_team_id: int | None = Field(default=None)  # Team number (1, 2, etc.)
    bracket_format: str | None = Field(default=None)  # e.g., "1v1", "2v2", "3v3", "ffa"

    # Relationships
    game: Games = Relationship()
    players: list[MatchPlayer] = Relationship(back_populates="match")
    teams: list[MatchTeam] = Relationship(back_populates="match")
