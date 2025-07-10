from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.constants import CASCADE
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.guild import Guilds


class AutoReAssign(SQLModel, table=True):

    guild_id: int = Field(foreign_key=get_foreign_key(Guilds, "id"), ondelete=CASCADE, primary_key=True)
