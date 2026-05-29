from __future__ import annotations

from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.guild import Guilds
from wd_db.tables.user import Users


class SyncBanBannedBy(SQLModel, table=True):
    guild_id: int = Field(foreign_key=get_foreign_key(Guilds), unique=True)
    user_id: int = Field(foreign_key=get_foreign_key(Users), unique=True)
    reason: str | None
