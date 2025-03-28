from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import GAMES_NAME, USERS_ID


class LookingForGroup(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key=USERS_ID)
    game_name: str = Field(foreign_key=GAMES_NAME)
