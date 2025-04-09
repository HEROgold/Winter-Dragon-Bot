
from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.command import Commands
from winter_dragon.database.tables.guild import Guilds


class GuildCommands(SQLModel, table=True):

    guild_id: int = Field(foreign_key=get_foreign_key(Guilds, "id"), primary_key=True)
    command_id: int = Field(foreign_key=get_foreign_key(Commands, "id"), primary_key=True)

    @property
    def id(self) -> int:
        """Get the id of the guild."""
        return self.guild_id
