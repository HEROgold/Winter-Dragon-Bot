from datetime import UTC, datetime, timedelta

from sqlmodel import Field, SQLModel, select

from database.tables.definitions import USERS_ID


class Presence(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key=USERS_ID)
    status: str
    date_time: datetime

    @staticmethod
    def remove_old_presences(member_id: int, days: int = 265) -> None:
        """Remove old presences present in the database, if they are older then a year."""
        from database import session

        with session:
            db_presences = session.exec(select(Presence).where(Presence.user_id == member_id)).all()
            for presence in db_presences:
                if (presence.date_time + timedelta(days=days)).astimezone(UTC) >= datetime.now(UTC):
                    session.delete(presence)
            session.commit()
