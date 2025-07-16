from __future__ import annotations

from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.game import Games

from .lobbystatus import LobbyStatus


class Lobbies(SQLModel, table=True):

    game: str | None = Field(foreign_key=get_foreign_key(Games, "name"), nullable=True)
    status: str = Field(foreign_key=get_foreign_key(LobbyStatus, "status"))
