

from sqlmodel import Field, Relationship

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.channel import Channels


class AutoChannels(SQLModel, table=True):
    channel_id: int = Field(foreign_key=get_foreign_key(Channels), primary_key=True)
    channel: Channels = Relationship()
