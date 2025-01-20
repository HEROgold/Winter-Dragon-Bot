import enum

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base


class LobbyStatusEnum(enum.Enum):
    CREATED = "created"
    WAITING = "waiting"
    BUSY = "busy"
    ENDED = "ended"


class LobbyStatus(Base):
    __tablename__ = "lobby_status"

    status: Mapped[str] = mapped_column(Enum(LobbyStatusEnum), primary_key=True)
