from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import CHANNELS_ID, GUILDS_ID


class Welcome(SQLModel, table=True):
    guild_id: int = Field(foreign_key=GUILDS_ID, primary_key=True)
    channel_id: int = Field(foreign_key=CHANNELS_ID, primary_key=True)
    message: str
    enabled: bool
