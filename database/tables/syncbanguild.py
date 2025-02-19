from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import GUILDS_ID


class SyncBanGuild(Base):
    __tablename__ = "sync_ban_guilds"

    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
