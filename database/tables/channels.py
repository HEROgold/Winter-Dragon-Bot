from typing import TYPE_CHECKING, Self

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.tables import Base, session
from database.tables.guilds import Guild


if TYPE_CHECKING:
    from database.tables.messages import Message


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    name: Mapped[str] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(String(50), nullable=True) # TODO: Use an enum matching discord's channels.
    guild_id: Mapped[int | None] = mapped_column(ForeignKey(Guild.id), nullable=True)

    messages: Mapped[list["Message"]] = relationship(back_populates="channel")
    guild: Mapped["Guild"] = relationship(back_populates="channels", foreign_keys=[guild_id])


    @classmethod
    def update(cls, channel: Self) -> None:
        # TODO: Update whenever the bot hears a discord channel update event > on_channel_update listener
        with session:
            if db_channel := session.query(Channel).where(Channel.id == channel.id).first():
                db_channel.id = channel.id
                db_channel.name = channel.name
                db_channel.type = channel.type
                db_channel.guild_id = channel.guild_id
            else:
                session.add(channel)
            session.commit()


class AutoChannel(Base):
    __tablename__ = "autochannels"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=False)
    channel_id: Mapped[int] = mapped_column(ForeignKey(Channel.id))


class AutoChannelSettings(Base):
    __tablename__ = "autochannel_settings"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=False)
    channel_name: Mapped[str] = mapped_column(Text)
    channel_limit: Mapped[int] = mapped_column(Integer)
