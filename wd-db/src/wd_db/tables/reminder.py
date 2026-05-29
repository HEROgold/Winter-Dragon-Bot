from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.user import Users


if TYPE_CHECKING:
    from datetime import datetime, timedelta


class Reminder(SQLModel, table=True):
    content: str
    user_id: int = Field(foreign_key=get_foreign_key(Users), ondelete="CASCADE")
    timestamp: datetime


class TimedReminder(SQLModel, table=True):
    content: str
    user_id: int = Field(foreign_key=get_foreign_key(Users), ondelete="CASCADE")
    timestamp: datetime
    repeat_every: timedelta
