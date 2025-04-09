
from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.lobby import Lobbies
from winter_dragon.database.tables.user import Users


class AssociationUserLobby(SQLModel, table=True):

    lobby_id: int = Field(foreign_key=get_foreign_key(Lobbies, "id"), primary_key=True)
    user_id: int = Field(foreign_key=get_foreign_key(Users, "id"), primary_key=True)
