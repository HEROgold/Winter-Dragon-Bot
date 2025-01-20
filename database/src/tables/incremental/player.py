from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import USERS_ID


class Player(Base):
    __tablename__ = "incremental_players"

    id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True)
    last_collection: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))
