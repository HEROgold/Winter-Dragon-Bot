from sqlalchemy import Column, ForeignKey
from sqlmodel import Field

from winter_dragon.database.extension.model import DiscordID
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.channel import Channels
from winter_dragon.database.tables.user import Users


class Messages(DiscordID, table=True):

    content: str
    user_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users), ondelete="CASCADE")))
    channel_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Channels)), nullable=True))
