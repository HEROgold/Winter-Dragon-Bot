from __future__ import annotations

from datetime import datetime

from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.user import Users


class CarFuels(SQLModel, table=True):
    user_id: int = Field(foreign_key=get_foreign_key(Users), ondelete="CASCADE")
    amount: float
    distance: float
    price: float
    timestamp: datetime = Field(default_factory=datetime.now)
