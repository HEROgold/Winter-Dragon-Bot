from typing import Self

from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from tools.main_log import sql_logger as logger


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)

    @classmethod
    def fetch_user(cls, id_: int) -> Self:
        """Find existing or create new user, and return it

        Args:
            id (int): Identifier for the user.
        """
        from database import session

        with session:
            logger.debug(f"Looking for user {id_=}")

            if user := session.query(cls).where(cls.id == id_).first():
                logger.debug(f"Returning user {id_=}")
                return user

            logger.debug(f"Creating user {id_=}")
            session.add(cls(id=id_))
            session.commit()
            return session.query(cls).where(cls.id == id_).first()  # type: ignore
