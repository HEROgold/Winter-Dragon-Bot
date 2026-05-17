

from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.game import Games

from .lobbystatus import LobbyStatus


class Lobbies(SQLModel, table=True):
    game_id: int | None = Field(foreign_key=get_foreign_key(Games), nullable=True)
    status: LobbyStatus = Field(default=LobbyStatus.CREATED)
