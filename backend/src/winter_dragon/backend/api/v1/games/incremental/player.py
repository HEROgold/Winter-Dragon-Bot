from datetime import UTC, datetime

from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.user import Users


class Players(SQLModel, table=True):

    id: int = Field(foreign_key=get_foreign_key(Users, "id"), primary_key=True)
    last_collection: datetime = Field(default=datetime.now(tz=UTC))
