from __future__ import annotations

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.channel import Channels
from wd_db.tables.guild import Guilds


class Welcome(SQLModel, table=True):
    guild_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Guilds)), unique=True))
    channel_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Channels)), unique=True))
    message: str
    enabled: bool
