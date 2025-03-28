from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import GAMES_NAME, USERS_ID


class ResultDuels(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    game: str = Field(foreign_key=GAMES_NAME)
    player: int = Field(foreign_key=USERS_ID)
    winner: bool
