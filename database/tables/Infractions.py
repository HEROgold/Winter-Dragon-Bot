from typing import Self

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.Base import Base
from database.tables.definitions import USERS_ID
from tools.main_log import sql_logger as logger


class Infractions(Base):
    __tablename__ = "infractions"

    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True)
    infraction_count: Mapped[int] = mapped_column(Integer, default=0)

    @classmethod
    def add_infraction_count(cls, user_id: int, amount: int) -> None:
        """Add an infraction to a user, if it isn't in this table add it"""
        from database.session import session

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
        from database.session import session

        with session:
            logger.debug(f"Looking for user {id_=}")

            if user := session.query(cls).where(cls.id == id_).first():
                logger.debug(f"Returning user {id_=}")
                return user

            logger.debug(f"Creating user {id_=}")
            session.add(cls(id=id_))
            session.commit()
            return session.query(cls).where(cls.id == id_).first()  # type: ignore
