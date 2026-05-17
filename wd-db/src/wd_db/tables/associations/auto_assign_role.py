

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.guild import Guilds
from wd_db.tables.role import Roles


class AutoAssignRole(SQLModel, table=True):
    role_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Roles)), primary_key=True))
    guild_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Guilds)), primary_key=True))
