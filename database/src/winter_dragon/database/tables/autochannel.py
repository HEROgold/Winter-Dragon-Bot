from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.channel import Channels


class AutoChannels(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    channel_id: int = Field(foreign_key=get_foreign_key(Channels, "id"))
