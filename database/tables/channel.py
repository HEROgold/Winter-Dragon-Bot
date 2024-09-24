from typing import Self

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import GUILDS_ID


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    name: Mapped[str] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(String(50), nullable=True)  # TODO: Use an enum matching discord's channels.
    guild_id: Mapped[int | None] = mapped_column(ForeignKey(GUILDS_ID), nullable=True)


    @classmethod
    def update(cls, channel: Self) -> None:
        # TODO: Update whenever the bot hears a discord channel update event > on_channel_update listener
        from database import session

        with session:
            if db_channel := session.query(Channel).where(Channel.id == channel.id).first():
                db_channel.id = channel.id
                db_channel.name = channel.name
                db_channel.type = channel.type
                db_channel.guild_id = channel.guild_id
            else:
                session.add(channel)
            session.commit()
