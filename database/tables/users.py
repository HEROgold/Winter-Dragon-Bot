from datetime import UTC, datetime
from typing import Self

from flask_login import UserMixin
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.tables import Base, session
from database.tables.definitions import USER_ID
from database.tables.messages import Message  # noqa: TCH001
from database.tables.utility import Reminder  # noqa: TCH001
from tools.main_log import sql_logger as logger


class User(Base, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)

    messages: Mapped[list["Message"]] = relationship(back_populates="user")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="user")

    @classmethod
    def fetch_user(cls, id_: int) -> Self:
        """Find existing or create new user, and return it

        Args:
            id (int): Identifier for the user.
        """
        with session:
            logger.debug(f"Looking for user {id_=}")

            if user := session.query(cls).where(cls.id == id_).first():
                logger.debug(f"Returning user {id_=}")
                return user

            logger.debug(f"Creating user {id_=}")
            session.add(cls(id=id_))
            session.commit()
            return session.query(cls).where(cls.id == id_).first() # type: ignore

class SyncBan(Base):
    __tablename__ = "synced_bans"

    user_id: Mapped[int] = mapped_column(ForeignKey(USER_ID), primary_key=True)


class Infractions(Base):
    __tablename__ = "infractions"

    user_id: Mapped[int] = mapped_column(ForeignKey(USER_ID), primary_key=True)
    infraction_count: Mapped[int] = mapped_column(Integer, default=0)

    @classmethod
    def add_infraction_count(cls, user_id: int, amount: int) -> None:
        """Add an infraction to a user, if it isn't in this table add it"""
        with session:
            infraction = session.query(cls).where(cls.user_id == user_id).first()

            if infraction is None:
                infraction = cls(user_id=user_id, infraction_count=0)
                session.add(infraction)

            infraction.infraction_count += amount
            session.commit()


    @classmethod
    def fetch_user(cls, id_: int) -> Self:
        """Find existing or create new user, and return it

        Args:
            id (int): Identifier for the user.
        """
        with session:
            logger.debug(f"Looking for user {id_=}")

            if user := session.query(cls).where(cls.id == id_).first():
                logger.debug(f"Returning user {id_=}")
                return user

            logger.debug(f"Creating user {id_=}")
            session.add(cls(id=id_))
            session.commit()
            return session.query(cls).where(cls.id == id_).first() # type: ignore


class Presence(Base):
    __tablename__ = "presence"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USER_ID))
    status: Mapped[str] = mapped_column(String(15))
    date_time: Mapped[datetime] = mapped_column(DateTime)


    @staticmethod
    def remove_old_presences(member_id: int, days: int = 265) -> None:
        """
        Removes old presences present in the database, if they are older then a year

        Parameters
        -----------
        :param:`member`: :class:`int`
            The Member_id to clean

        :param:`days`: :class:`int`
            The amount of days ago to remove, defaults to (256)
        """
        with session:
            db_presences = session.query(Presence).where(Presence.user_id == member_id).all()
            for presence in db_presences:
                if (presence.date_time + datetime.timedelta(days=days)) >= datetime.now(UTC):
                    session.delete(presence)
            session.commit()


class SteamUser(Base):
    __tablename__ = "steam_users"

    id: Mapped[int] = mapped_column(ForeignKey(USER_ID), primary_key=True, unique=True)
