"""TeamComposition table - tracks historical team compositions and success."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key


if TYPE_CHECKING:
    from wd_db.tables.game import Games
    from wd_db.tables.matchmaking.team_composition_player import TeamCompositionPlayer
    from wd_db.tables.user import Users
else:
    from wd_db.tables import Games
    from wd_db.tables.matchmaking.team_composition_player import TeamCompositionPlayer


class TeamComposition(SQLModel, table=True):
    """Historical record of team compositions for future reference.

    6NF: Facts about a specific team composition that played together.
    Players are linked via TeamCompositionPlayer association table.
    """

    game_id: int = Field(foreign_key=get_foreign_key(Games), index=True)

    # Statistics for this exact composition
    times_played: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    win_rate: float = Field(default=0.0)
    avg_team_score: float = Field(default=0.0)

    # Relationships
    game: Games = Relationship()
    players: list["Users"] = Relationship(link_model=TeamCompositionPlayer)
