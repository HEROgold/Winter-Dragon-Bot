from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.constants import CASCADE
from database.tables.Base import Base
from database.tables.definitions import GAMES_NAME, LOBBY_STATUS, MESSAGES_ID


class Lobby(Base):
    __tablename__ = "lobbies"

    id: Mapped[int] = mapped_column(ForeignKey(MESSAGES_ID, ondelete=CASCADE), primary_key=True, unique=True)
    game: Mapped[str] = mapped_column(ForeignKey(GAMES_NAME))
    status: Mapped[str] = mapped_column(ForeignKey(LOBBY_STATUS))
