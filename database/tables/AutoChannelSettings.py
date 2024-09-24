from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.Base import Base


class AutoChannelSettings(Base):
    __tablename__ = "autochannel_settings"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=False)
    channel_name: Mapped[str] = mapped_column(Text)
    channel_limit: Mapped[int] = mapped_column(Integer)
