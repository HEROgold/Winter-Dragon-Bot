from datetime import UTC, datetime, timedelta

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel, select
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.user import Users


class Presence(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users, "id"))))
    status: str
    date_time: datetime

    @staticmethod
    def remove_old_presences(member_id: int, days: int = 265) -> None:
        """Remove old presences present in the database, if they are older then a year."""
        from winter_dragon.database import session

        with session:
            db_presences = session.exec(select(Presence).where(Presence.user_id == member_id)).all()
            for presence in db_presences:
                if (presence.date_time + timedelta(days=days)).astimezone(UTC) >= datetime.now(UTC):
                    session.delete(presence)
            session.commit()
