from datetime import datetime, timedelta

from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.user import Users


class Reminder(SQLModel, table=True):

    content: str
    user_id: int = Field(foreign_key=get_foreign_key(Users), ondelete="CASCADE")
    timestamp: datetime
    repeats: timedelta | None = Field(default=None)
