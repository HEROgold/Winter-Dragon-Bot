


from datetime import datetime, timedelta

from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.user import Users


class Reminder(SQLModel, table=True):
    content: str
    user_id: int = Field(foreign_key=get_foreign_key(Users), ondelete="CASCADE")
    timestamp: datetime


class TimedReminder(SQLModel, table=True):
    content: str
    user_id: int = Field(foreign_key=get_foreign_key(Users), ondelete="CASCADE")
    timestamp: datetime
    repeat_every: timedelta
