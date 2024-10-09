

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, autoincrement=True)
    branch: Mapped[int] = mapped_column(String)
