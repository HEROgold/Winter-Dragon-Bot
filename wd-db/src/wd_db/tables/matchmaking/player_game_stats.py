"""PlayerGameStats table - aggregated statistics per player per game."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key


if TYPE_CHECKING:
    from wd_db.tables.game import Games
    from wd_db.tables.user import Users
else:
    from wd_db.tables import Games, Users


class PlayerGameStats(SQLModel, table=True):
    """Aggregated player statistics for a specific game.

    6NF: Derived/aggregated facts about player performance in a game.
    This is computed from match history but stored for performance.
    """

    user_id: int = Field(foreign_key=get_foreign_key(Users), index=True)
    game_id: int = Field(foreign_key=get_foreign_key(Games), index=True)

    # Aggregated statistics
    total_matches: int = Field(default=0)
    total_wins: int = Field(default=0)
    total_losses: int = Field(default=0)
    win_rate: float = Field(default=0.0)  # Computed: wins / total_matches
    avg_score: float = Field(default=0.0)  # Average individual score
    skill_rating: float = Field(default=1000.0)  # ELO-like rating

    # Relationships
    user: Users = Relationship()
    game: Games = Relationship()
