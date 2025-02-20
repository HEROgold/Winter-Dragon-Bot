from sqlmodel import Field, SQLModel

from database.constants import CASCADE
from database.tables.definitions import GUILDS_ID


class AutoReAssign(SQLModel, table=True):

    guild_id = Field(foreign_key=GUILDS_ID, ondelete=CASCADE, primary_key=True)
