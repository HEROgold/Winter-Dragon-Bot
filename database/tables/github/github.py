

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base


# TODO: do we need this?
class GitHub(Base):
    __tablename__ = "github"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, autoincrement=True)
    branch: Mapped[int] = mapped_column(Integer)
    tag: Mapped[int] = mapped_column(Integer)
