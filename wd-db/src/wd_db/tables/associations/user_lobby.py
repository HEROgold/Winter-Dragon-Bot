from __future__ import annotations

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.lobby import Lobbies
from wd_db.tables.user import Users


class AssociationUserLobby(SQLModel, table=True):
    lobby_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Lobbies)), unique=True))
    user_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users), ondelete="CASCADE"), unique=True))
