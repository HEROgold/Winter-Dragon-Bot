from typing import Self

from sqlmodel import Field, SQLModel, select

from database.channels import ChannelTypes
from database.tables.definitions import GUILDS_ID


class Channel(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    name: str
    type: ChannelTypes
    guild_id: int = Field(foreign_key=GUILDS_ID)


    @classmethod
    def update(cls, channel: Self) -> None:
        """Update a channel in the database."""
        from database import session

        with session:
            if db_channel := session.exec(select(Channel).where(Channel.id == channel.id)).first():
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
