

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field

from wd_db.extension.model import DiscordID
from wd_db.keys import get_foreign_key
from wd_db.tables.channel import Channels
from wd_db.tables.user import Users


class Messages(DiscordID, table=True):
    content: str
    user_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users), ondelete="CASCADE")))
    channel_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Channels)), nullable=True))
