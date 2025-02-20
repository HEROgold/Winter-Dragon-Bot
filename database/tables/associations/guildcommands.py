from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import COMMANDS_ID, GUILDS_ID


class GuildCommands(SQLModel, table=True):

    guild_id = 
    command_id = 
