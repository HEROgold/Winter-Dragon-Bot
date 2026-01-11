from sqlalchemy import Column, ForeignKey
from sqlmodel import Field

from winter_dragon.database.channel_types import Tags
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.channel import Channels


class ChannelTag(SQLModel, table=True):
    """Association table linking channels to their tags."""

    channel_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Channels), ondelete="CASCADE"), primary_key=True))
    tag: Tags
