from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import GUILDS_ID, ROLES_ID, USERS_ID


class UserRoles(SQLModel, table=True):

    role_id: int = Field(foreign_key=ROLES_ID, primary_key=True)
    guild_id: int = Field(foreign_key=GUILDS_ID, primary_key=True)
    user_id: int = Field(foreign_key=USERS_ID, primary_key=True)

