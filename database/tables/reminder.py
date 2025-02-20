from datetime import datetime

from sqlmodel import Field, SQLModel

from database.tables.definitions import USERS_ID


class Reminder(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    content: str = Field()
    user_id: int = Field(foreign_key=USERS_ID)
    timestamp: datetime = Field()
