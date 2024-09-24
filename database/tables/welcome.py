from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import CHANNELS_ID, GUILDS_ID


class Welcome(Base):
    __tablename__ = "welcome"

    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID))
    message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean)
