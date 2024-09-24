from typing import TYPE_CHECKING, Self

from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.tables.Base import Base
from tools.main_log import sql_logger as logger


if TYPE_CHECKING:
    from database.tables.Message import Message
    from database.tables.Reminder import Reminder


class User(Base):
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
