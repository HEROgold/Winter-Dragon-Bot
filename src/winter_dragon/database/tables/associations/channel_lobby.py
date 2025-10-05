
from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.channel import Channels
from winter_dragon.database.tables.lobby import Lobbies


class ChannelLobby(SQLModel, table=True):
    channel_id: int = Field(foreign_key=get_foreign_key(Channels))
    lobby_id: int = Field(foreign_key=get_foreign_key(Lobbies))
