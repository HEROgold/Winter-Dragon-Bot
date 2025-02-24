
from sqlmodel import Field, SQLModel

from database.tables.definitions import GUILDS_ID, ROLES_ID


class GuildRoles(SQLModel, table=True):

    guild_id = Field(foreign_key=GUILDS_ID)
    role_id = Field(foreign_key=ROLES_ID)
