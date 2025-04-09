
from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.guild import Guilds
from winter_dragon.database.tables.role import Roles


class GuildRoles(SQLModel, table=True):

    guild_id: int = Field(foreign_key=get_foreign_key(Guilds, "id"), primary_key=True)
    role_id: int = Field(foreign_key=get_foreign_key(Roles, "id"), primary_key=True)
