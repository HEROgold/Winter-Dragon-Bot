"""MatchTeam table - stores team-level statistics for matches."""

from typing import TYPE_CHECKING

from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key


if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped, relationship

    from winter_dragon.database.tables.matchmaking.game_match import GameMatch
else:
    from winter_dragon.database.tables.matchmaking import GameMatch


class MatchTeam(SQLModel, table=True):
    """Represents team-level statistics for a match.

    6NF: Only facts about team performance in a specific match.
    """

    __tablename__ = "match_team"

    match_id: int = Field(foreign_key=get_foreign_key(GameMatch), index=True)
    team_number: int = Field(default=1)
    team_score: int | None = Field(default=None)  # Total team score
    won: bool = Field(default=False)

    # Relationships
    if TYPE_CHECKING:
        match: Mapped["GameMatch"] = relationship(back_populates="teams")
