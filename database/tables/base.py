from sqlalchemy.orm import DeclarativeBase

from bot._types.mixins import LoggerMixin


class Base(DeclarativeBase, LoggerMixin):
    """Subclass of DeclarativeBase with customizations."""

    def __repr__(self) -> str:
        return str(self.__dict__)
