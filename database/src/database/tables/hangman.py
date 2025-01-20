from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import MESSAGES_ID


class Hangman(Base):
    __tablename__ = "hangmen"

    id: Mapped[int] = mapped_column(ForeignKey(MESSAGES_ID), primary_key=True, unique=True)
    word: Mapped[str] = mapped_column(String(24))
    letters: Mapped[str] = mapped_column(String(24), nullable=True)
