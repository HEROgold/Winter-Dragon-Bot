from typing import Self

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import USERS_ID


class Infractions(Base):
    __tablename__ = "infractions"

    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True)
    infraction_count: Mapped[int] = mapped_column(Integer, default=0)

    @classmethod
    def add_infraction_count(cls, user_id: int, amount: int) -> None:
        """Add an infraction to a user, if it isn't in this table add it"""
        from database import session

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
        from database import session

        with session:
            if user := session.query(cls).where(cls.id == id_).first():
                return user

            inst = cls(id=id_)
            session.add(inst)
            session.commit()
            return inst
