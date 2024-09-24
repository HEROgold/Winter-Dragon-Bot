from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.Base import Base


class WyrQuestion(Base):
    __tablename__ = "wyr_questions"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    value: Mapped[str] = mapped_column(String())
