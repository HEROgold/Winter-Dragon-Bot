from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.user import Users


class Players(SQLModel, table=True):
    """Table for storing player data."""

    user_id: int = Field(foreign_key=get_foreign_key(Users), ondelete="CASCADE", primary_key=True)
    last_collection: datetime = Field(default=datetime.now(tz=UTC))
