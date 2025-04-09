from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.game import Games
from winter_dragon.database.tables.user import Users


class ResultDuels(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    game: str = Field(foreign_key=get_foreign_key(Games, "name"))
    player: int = Field(foreign_key=get_foreign_key(Users, "id"))
    winner: bool
