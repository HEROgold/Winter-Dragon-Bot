from sqlalchemy import BigInteger, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.channel import Channels


class AutoChannels(SQLModel, table=True):

    id: int = Field(sa_column=Column(BigInteger(), primary_key=True))
    channel_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Channels, "id"))))

    channel: Channels = Relationship()
