import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base


class SteamSale(Base):
    __tablename__ = "steam_sales"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    title: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(String(200))
    sale_percent: Mapped[int] = mapped_column(Integer)
    final_price: Mapped[int] = mapped_column(Float)  # (5, True, 2)
    is_dlc: Mapped[bool] = mapped_column(Boolean)
    is_bundle: Mapped[bool] = mapped_column(Boolean)
    update_datetime: Mapped[datetime.datetime] = mapped_column(DateTime)
