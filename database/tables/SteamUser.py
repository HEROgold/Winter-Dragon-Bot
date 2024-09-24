from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.Base import Base
from database.tables.definitions import USERS_ID


class SteamUser(Base):
    __tablename__ = "steam_users"

    id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True, unique=True)
