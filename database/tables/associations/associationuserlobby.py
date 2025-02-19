from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.constants import CASCADE
from database.tables.base import Base
from database.tables.definitions import LOBBIES_ID, USERS_ID


class AssociationUserLobby(Base):
    __tablename__ = "association_users_lobbies"

    lobby_id: Mapped[int] = mapped_column(ForeignKey(LOBBIES_ID, ondelete=CASCADE), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True)
