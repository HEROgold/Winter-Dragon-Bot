"""MatchPlayer table - stores player participation in matches."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key


if TYPE_CHECKING:
    from wd_db.tables.matchmaking.game_match import GameMatch
    from wd_db.tables.user import Users
else:
    from wd_db.tables import Users


class MatchPlayer(SQLModel, table=True):
    """Represents a player's participation in a specific match.

    6NF: Only facts about player participation in this specific match.
    """

    match_id: int = Field(foreign_key="gamematch.id", index=True)
    user_id: int = Field(foreign_key=get_foreign_key(Users), index=True)
    team_number: int = Field(default=1)  # Which team they were on (1, 2, etc.)
    individual_score: int | None = Field(default=None)  # Score/kills/points in this match
    won: bool = Field(default=False)

    # Relationships
    match: GameMatch = Relationship(back_populates="players")
    user: Users = Relationship()
