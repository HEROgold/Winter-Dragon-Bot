

from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.guild import Guilds


class SyncBanGuild(SQLModel, table=True):
    """Track guilds that have subscribed to the sync ban feature."""

    guild_id: int = Field(foreign_key=get_foreign_key(Guilds), primary_key=True)
