"""MatchPlayer table - stores player participation in matches."""

from typing import TYPE_CHECKING

from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key


if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped, relationship

    from winter_dragon.database.tables.matchmaking.game_match import GameMatch
    from winter_dragon.database.tables.user import Users
else:
    from winter_dragon.database.tables import Users
    from winter_dragon.database.tables.matchmaking import GameMatch


class MatchPlayer(SQLModel, table=True):
    """Represents a player's participation in a specific match.

    6NF: Only facts about player participation in this specific match.
    """

    __tablename__ = "match_player"

    match_id: int = Field(foreign_key=get_foreign_key(GameMatch), index=True)
    user_id: int = Field(foreign_key=get_foreign_key(Users), index=True)
    team_number: int = Field(default=1)  # Which team they were on (1, 2, etc.)
    individual_score: int | None = Field(default=None)  # Score/kills/points in this match
    won: bool = Field(default=False)

    # Relationships
    if TYPE_CHECKING:
        match: Mapped["GameMatch"] = relationship(back_populates="players")
        user: Mapped["Users"] = relationship()
