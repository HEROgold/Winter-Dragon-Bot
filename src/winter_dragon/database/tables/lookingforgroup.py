from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.game import Games
from winter_dragon.database.tables.user import Users


class LookingForGroup(SQLModel, table=True):
    user_id: int = Field(foreign_key=get_foreign_key(Users), ondelete="CASCADE")
    game_id: int = Field(foreign_key=get_foreign_key(Games))
