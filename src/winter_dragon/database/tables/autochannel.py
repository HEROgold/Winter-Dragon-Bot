from sqlmodel import Field, Relationship

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.channel import Channels


class AutoChannels(SQLModel, table=True):
    channel_id: int = Field(foreign_key=get_foreign_key(Channels), primary_key=True)
    channel: Channels = Relationship()
