from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base


class NhieQuestion(Base):
    __tablename__ = "nhie_questions"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    value: Mapped[str] = mapped_column(String())
