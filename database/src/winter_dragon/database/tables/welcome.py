from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.channel import Channels
from winter_dragon.database.tables.guild import Guilds


class Welcome(SQLModel, table=True):
    guild_id: int = Field(foreign_key=get_foreign_key(Guilds, "id"), primary_key=True)
    channel_id: int = Field(foreign_key=get_foreign_key(Channels, "id"), primary_key=True)
    message: str
    enabled: bool
