
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import USERS_ID


class UserMoney(Base):
    __tablename__ = "incremental_money"

    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True)
    currency: Mapped[str] = mapped_column(Integer, default=0, primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)
