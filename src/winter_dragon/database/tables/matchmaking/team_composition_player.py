"""Association table for team composition players."""

from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables import Users
from winter_dragon.database.tables.matchmaking import TeamComposition


class TeamCompositionPlayer(SQLModel, table=True):
    """Association table linking team compositions to players.

    This represents a many-to-many relationship between team compositions and users.
    """

    __tablename__ = "team_composition_player"

    composition_id: int = Field(foreign_key=get_foreign_key(TeamComposition), primary_key=True, index=True)
    user_id: int = Field(foreign_key=get_foreign_key(Users), primary_key=True, index=True)
