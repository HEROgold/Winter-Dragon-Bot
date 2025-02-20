from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import GUILDS_ID, ROLES_ID


class GuildRoles(SQLModel, table=True):

    guild_id = 
    role_id = 
