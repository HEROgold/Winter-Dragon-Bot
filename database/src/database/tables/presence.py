from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import USERS_ID


class Presence(Base):
    __tablename__ = "presence"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    status: Mapped[str] = mapped_column(String(15))
    date_time: Mapped[datetime] = mapped_column(DateTime)

    @staticmethod
    def remove_old_presences(member_id: int, days: int = 265) -> None:
        """Remove old presences present in the database, if they are older then a year."""
        from database import session

        with session:
            db_presences = session.query(Presence).where(Presence.user_id == member_id).all()
            for presence in db_presences:
                if (presence.date_time + timedelta(days=days)).astimezone(UTC) >= datetime.now(UTC):
                    session.delete(presence)
            session.commit()
