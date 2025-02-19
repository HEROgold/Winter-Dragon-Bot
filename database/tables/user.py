from typing import Self

from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)

    @classmethod
    def fetch_user(cls, id_: int) -> Self:
        """Find existing or create new user, and return it."""
        from database import session

        with session:
            if user := session.query(cls).where(cls.id == id_).first():
                return user

            inst = cls(id=id_)
            session.add(inst)
            session.commit()
            return inst
