from sqlalchemy import Column, ForeignKey
from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.command import Commands
from winter_dragon.database.tables.guild import Guilds


class GuildCommands(SQLModel, table=True):
    guild_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Guilds)), primary_key=True))
    command_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Commands)), primary_key=True))
