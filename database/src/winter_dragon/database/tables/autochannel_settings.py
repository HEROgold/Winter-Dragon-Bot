from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.user import Users


class AutoChannelSettings(SQLModel, table=True):

    user_id: int | None = Field(foreign_key=get_foreign_key(Users, "id"), default=None, primary_key=True)
    channel_name: str
    channel_limit: int
