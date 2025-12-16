from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.guild import Guilds
from winter_dragon.database.tables.user import Users


class SyncBanBannedBy(SQLModel, table=True):
    guild_id: int = Field(foreign_key=get_foreign_key(Guilds), primary_key=True)
    user_id: int = Field(foreign_key=get_foreign_key(Users), primary_key=True)
    reason: str | None
