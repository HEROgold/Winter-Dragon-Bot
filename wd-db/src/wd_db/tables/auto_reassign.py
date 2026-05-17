

from sqlmodel import Field

from wd_db.constants import CASCADE
from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.guild import Guilds


class AutoReAssign(SQLModel, table=True):
    guild_id: int = Field(foreign_key=get_foreign_key(Guilds), ondelete=CASCADE, primary_key=True)
