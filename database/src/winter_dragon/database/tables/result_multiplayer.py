from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.game import Games
from winter_dragon.database.tables.user import Users


class ResultMassiveMultiplayer(SQLModel, table=True):

    game: str = Field(foreign_key=get_foreign_key(Games, "name"))
    player: int = Field(foreign_key=get_foreign_key(Users), ondelete="CASCADE")
    placement: int
