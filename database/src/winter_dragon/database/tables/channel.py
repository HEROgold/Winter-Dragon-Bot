from typing import Self

from sqlalchemy import BigInteger, Column, ForeignKey
from sqlmodel import Field, SQLModel, select
from winter_dragon.database.channeltypes import ChannelTypes
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.guild import Guilds


class Channels(SQLModel, table=True):

    id: int | None = Field(sa_column=Column(BigInteger(), primary_key=True), default=None)
    name: str
    type: ChannelTypes | None
    guild_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Guilds, "id"))))


    @classmethod
    def update(cls, channel: Self) -> None:
        """Update a channel in the database."""
        from winter_dragon.database import session
        with session:
            if db_channel := session.exec(select(Channels).where(Channels.id == channel.id)).first():
                db_channel.id = channel.id
                db_channel.name = channel.name
                db_channel.guild_id = channel.guild_id
                if channel.type != ChannelTypes.UNKNOWN:
                    db_channel.type = channel.type
            else:
                session.add(channel)
            session.commit()
