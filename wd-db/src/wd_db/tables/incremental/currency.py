from __future__ import annotations

from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.user import Users


class UserMoney(SQLModel, table=True):
    user_id: int = Field(foreign_key=get_foreign_key(Users), ondelete="CASCADE", unique=True)
    currency: str = Field(unique=True)
    value: int = Field(default=0)
