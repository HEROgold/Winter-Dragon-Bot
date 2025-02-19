
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import USERS_ID


class UserGenerator(Base):
    __tablename__ = "incremental_generators"

    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True)
    generator_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)

