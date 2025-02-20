from sqlmodel import Field, SQLModel

from database.tables.definitions import GAMES_NAME, LOBBY_STATUS


class Lobby(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    game: str = Field(foreign_key=GAMES_NAME)
    status: str = Field(foreign_key=LOBBY_STATUS)
