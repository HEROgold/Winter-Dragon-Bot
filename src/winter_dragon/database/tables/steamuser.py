from datetime import UTC, datetime

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.user import Users


class SteamUsers(SQLModel, table=True):
    """Table for users who want to be notified about steam sales."""

    user_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users), ondelete="CASCADE"), primary_key=True))
    sale_threshold: int = Field(default=100, description="Minimum discount percentage required before notifying the user.")
    last_notification: datetime = Field(
        default=datetime(2000, 1, 1, 0, 0, 0, tzinfo=UTC), description="Timestamp of the last notification sent to the user."
    )
