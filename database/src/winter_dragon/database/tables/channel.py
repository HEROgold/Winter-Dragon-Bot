
from sqlalchemy import Column, ForeignKey
from sqlmodel import Field
from winter_dragon.database.channeltypes import ChannelTypes
from winter_dragon.database.extension.model import DiscordID
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.guild import Guilds


class Channels(DiscordID, table=True):
    guild_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Guilds))))
    name: str
    type: ChannelTypes | None = None
