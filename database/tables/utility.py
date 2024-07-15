import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.tables import Base
from database.tables.definitions import USERS_ID


if TYPE_CHECKING:
    from database.tables.users import User
else:
    User = "users"


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    type: Mapped[str] = mapped_column(String(50))
    is_verified: Mapped[bool] = mapped_column(Boolean)
    content: Mapped[str] = mapped_column(String(2048))


class SteamSale(Base):
    __tablename__ = "steam_sales"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    title: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(String(200))
    sale_percent: Mapped[int] = mapped_column(Integer)
    final_price: Mapped[int] = mapped_column(Float) # (5, True, 2)
    is_dlc: Mapped[bool] = mapped_column(Boolean)
    is_bundle: Mapped[bool] = mapped_column(Boolean)
    update_datetime: Mapped[datetime.datetime] = mapped_column(DateTime)


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    content: Mapped[str] = mapped_column(String(2000))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="reminders", foreign_keys=[user_id])
