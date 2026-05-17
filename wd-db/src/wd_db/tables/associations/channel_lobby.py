

from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.channel import Channels
from wd_db.tables.lobby import Lobbies


class ChannelLobby(SQLModel, table=True):
    channel_id: int = Field(foreign_key=get_foreign_key(Channels))
    lobby_id: int = Field(foreign_key=get_foreign_key(Lobbies))
