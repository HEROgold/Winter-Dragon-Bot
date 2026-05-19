"""MatchTeam table - stores team-level statistics for matches."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from winter_dragon.database.extension.model import SQLModel


if TYPE_CHECKING:
    from winter_dragon.database.tables.matchmaking.game_match import GameMatch
else:
    pass  # GameMatch is imported via TYPE_CHECKING for type hints


class MatchTeam(SQLModel, table=True):
    """Represents team-level statistics for a match.

    6NF: Only facts about team performance in a specific match.
    """

    match_id: int = Field(foreign_key="gamematch.id", index=True)
    team_number: int = Field(default=1)
    team_score: int | None = Field(default=None)  # Total team score
    won: bool = Field(default=False)

    # Relationships
    match: GameMatch = Relationship(back_populates="teams")
