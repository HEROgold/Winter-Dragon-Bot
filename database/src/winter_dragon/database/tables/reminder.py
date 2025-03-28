from datetime import datetime

from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import USERS_ID


class Reminder(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    content: str
    user_id: int = Field(foreign_key=USERS_ID)
    timestamp: datetime
