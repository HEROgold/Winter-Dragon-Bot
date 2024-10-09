

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, autoincrement=True)
    tag: Mapped[int] = mapped_column(String)
