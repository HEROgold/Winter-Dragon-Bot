from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.guild import Guilds


class SyncBanGuild(SQLModel, table=True):

    guild_id: int = Field(foreign_key=get_foreign_key(Guilds, "id"), primary_key=True)

