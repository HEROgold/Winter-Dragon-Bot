
from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import COMMANDS_ID, GUILDS_ID


class GuildCommands(SQLModel, table=True):

    guild_id: int = Field(foreign_key=GUILDS_ID)
    command_id: int = Field(foreign_key=COMMANDS_ID)
