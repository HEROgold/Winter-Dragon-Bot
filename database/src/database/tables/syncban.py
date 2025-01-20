from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import USERS_ID


class SyncBan(Base):
    __tablename__ = "synced_bans"

    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True)
