from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import GUILDS_ID


class SyncBanGuild(SQLModel, table=True):

    guild_id: int = Field(foreign_key=GUILDS_ID, primary_key=True)

