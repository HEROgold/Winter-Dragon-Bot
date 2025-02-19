from typing import Self

from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.channels import ChannelTypes
from database.tables.base import Base
from database.tables.definitions import GUILDS_ID


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    name: Mapped[str] = mapped_column(String(50))
    type: Mapped[ChannelTypes] = mapped_column(Enum(ChannelTypes), default=ChannelTypes.UNKNOWN)
    guild_id: Mapped[int | None] = mapped_column(ForeignKey(GUILDS_ID), nullable=True)


    @classmethod
    def update(cls, channel: Self) -> None:
        from database import session

        with session:
            if db_channel := session.query(Channel).where(Channel.id == channel.id).first():
                db_channel.id = channel.id
                db_channel.name = channel.name
                db_channel.guild_id = channel.guild_id
                if channel.type != ChannelTypes.UNKNOWN:
                    db_channel.type = channel.type
            else:
                session.add(channel)
            channel.logger.debug("Updated channel", extra=channel.__dict__)
            # TODO @HEROgold: Verify the logger works as intended.
            # 000
            session.commit()
