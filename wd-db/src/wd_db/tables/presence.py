

from datetime import UTC, datetime, timedelta

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, select

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.user import Users


class Presence(SQLModel, table=True):
    user_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users), ondelete="CASCADE")))
    status: str
    date_time: datetime

    @classmethod
    def remove_old_presences(cls, member_id: int, days: int = 265) -> None:
        """Remove old presences present in the database, if they are older then a year."""
        db_presences = cls.session.exec(select(Presence).where(Presence.user_id == member_id)).all()
        for presence in db_presences:
            if (presence.date_time + timedelta(days=days)).astimezone(UTC) >= datetime.now(UTC):
                cls.session.delete(presence)
        cls.session.commit()
