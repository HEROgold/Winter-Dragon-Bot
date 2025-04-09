from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.channel import Channels
from winter_dragon.database.tables.user import Users


class Messages(SQLModel, table=True):

    id: int = Field(primary_key=True, unique=True)
    content: str
    user_id: int = Field(foreign_key=get_foreign_key(Users, "id"))
    channel_id: int = Field(foreign_key=get_foreign_key(Channels, "id"), nullable=True)
