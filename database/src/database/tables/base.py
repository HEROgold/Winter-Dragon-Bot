from sqlalchemy.orm import DeclarativeBase

from database.logger import LoggerMixin


class Base(DeclarativeBase, LoggerMixin):
    """Subclass of DeclarativeBase with customizations."""

    def __repr__(self) -> str:
        return str(self.__dict__)
