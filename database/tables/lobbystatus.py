import enum

from sqlmodel import SQLModel


class LobbyStatusEnum(enum.Enum):
    CREATED = "created"
    WAITING = "waiting"
    BUSY = "busy"
    ENDED = "ended"


class LobbyStatus(SQLModel, table=True):

    status: LobbyStatusEnum
