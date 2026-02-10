"""PlayerSynergy table - tracks player interaction statistics."""

from typing import TYPE_CHECKING

from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key


if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped, relationship

    from winter_dragon.database.tables.game import Games
    from winter_dragon.database.tables.user import Users
else:
    from winter_dragon.database.tables import Games, Users


class PlayerSynergy(SQLModel, table=True):
    """Tracks synergy/rivalry between two players in a specific game.

    6NF: Only facts about the interaction between two specific players in a game.
    """

    __tablename__ = "player_synergy"

    player1_id: int = Field(foreign_key=get_foreign_key(Users), index=True)
    player2_id: int = Field(foreign_key=get_foreign_key(Users), index=True)
    game_id: int = Field(foreign_key=get_foreign_key(Games), index=True)

    # Teammate statistics
    matches_as_teammates: int = Field(default=0)
    wins_as_teammates: int = Field(default=0)
    teammate_synergy: float = Field(default=0.0)  # Win rate when together

    # Opponent statistics
    matches_as_opponents: int = Field(default=0)
    player1_wins_vs_player2: int = Field(default=0)
    rivalry_factor: float = Field(default=0.0)  # How often player1 beats player2

    # Relationships
    if TYPE_CHECKING:
        player1: Mapped["Users"] = relationship(foreign_keys=[player1_id])
        player2: Mapped["Users"] = relationship(foreign_keys=[player2_id])
        game: Mapped["Games"] = relationship()
