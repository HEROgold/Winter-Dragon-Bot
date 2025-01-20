
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import USERS_ID


class CarFuel(Base):
    __tablename__ = "car_fuels"

    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True, unique=True)
    amount: Mapped[int] = mapped_column(Integer)
    distance: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
