"""TeamComposition table - tracks historical team compositions and success."""

from typing import TYPE_CHECKING

from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key


if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped, relationship

    from winter_dragon.database.tables.game import Games
    from winter_dragon.database.tables.user import Users
else:
    from winter_dragon.database.tables import Games


class TeamComposition(SQLModel, table=True):
    """Historical record of team compositions for future reference.

    6NF: Facts about a specific team composition that played together.
    Players are linked via TeamCompositionPlayer association table.
    """

    __tablename__ = "team_composition"

    game_id: int = Field(foreign_key=get_foreign_key(Games), index=True)

    # Statistics for this exact composition
    times_played: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    win_rate: float = Field(default=0.0)
    avg_team_score: float = Field(default=0.0)

    # Relationships
    if TYPE_CHECKING:
        game: Mapped["Games"] = relationship()
        players: Mapped[list["Users"]] = relationship(secondary="team_composition_player", back_populates="team_compositions")
