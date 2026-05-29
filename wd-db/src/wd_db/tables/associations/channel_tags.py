from __future__ import annotations

from sqlalchemy import Column, Enum, ForeignKey
from sqlmodel import Field

from wd_db.channel_types import Tags
from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.channel import Channels


class ChannelTag(SQLModel, table=True):
    """Association table linking channels to their tags."""

    channel_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Channels), ondelete="CASCADE"), unique=True))
    tag: Tags = Field(sa_column=Column(Enum(Tags), nullable=False))
