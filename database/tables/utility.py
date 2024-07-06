import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.tables import Base
from database.tables.channels import Channel
from database.tables.definitions import USERS_ID
from database.tables.messages import Message


if TYPE_CHECKING:
    from database.tables.users import User
else:
    User = "users"


class Poll(Base):
    # TODO: use discord's build in poll system
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey(Channel.id))
    message_id: Mapped[int] = mapped_column(ForeignKey(Message.id))
    content: Mapped[str] = mapped_column(Text)
    end_date: Mapped[datetime.datetime] = mapped_column(DateTime)


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
