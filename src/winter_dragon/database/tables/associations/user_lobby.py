from sqlalchemy import Column, ForeignKey
from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.lobby import Lobbies
from winter_dragon.database.tables.user import Users


class AssociationUserLobby(SQLModel, table=True):
    lobby_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Lobbies)), primary_key=True))
    user_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users), ondelete="CASCADE"), primary_key=True))
