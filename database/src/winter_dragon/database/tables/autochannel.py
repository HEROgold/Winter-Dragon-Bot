from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship
from winter_dragon.database.extension.model import DiscordID
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.channel import Channels


class AutoChannels(DiscordID, table=True):
    channel_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Channels, "id"))))
    channel: Channels = Relationship()
