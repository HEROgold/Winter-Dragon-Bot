from sqlmodel import Field, SQLModel
from winter_dragon.database.constants import CASCADE
from winter_dragon.database.tables.definitions import GUILDS_ID


class AutoReAssign(SQLModel, table=True):

    guild_id: int = Field(foreign_key=GUILDS_ID, ondelete=CASCADE, primary_key=True)
