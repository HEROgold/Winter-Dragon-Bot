from sqlmodel import Field, SQLModel

from database.constants import CASCADE
from database.tables.definitions import GUILDS_ID, ROLES_ID


class AutoAssignRole(SQLModel, table=True):

    role_id: int = Field(foreign_key=ROLES_ID, ondelete=CASCADE, primary_key=True)
    guild_id: int = Field(foreign_key=GUILDS_ID, primary_key=True)
