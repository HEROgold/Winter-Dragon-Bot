"""Association table for team composition players."""

from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.tables.user import Users


class TeamCompositionPlayer(SQLModel, table=True):
    """Association table linking team compositions to players.

    This represents a many-to-many relationship between team compositions and users.
    """

    composition_id: int = Field(foreign_key="teamcomposition.id", primary_key=True, index=True)
    user_id: int = Field(foreign_key=f"{Users.__tablename__}.id", primary_key=True, index=True)
