from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import COMMANDS_ID, GUILDS_ID


class GuildCommands(Base):
    __tablename__ = "guild_commands"

    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
    command_id: Mapped[int] = mapped_column(ForeignKey(COMMANDS_ID))
