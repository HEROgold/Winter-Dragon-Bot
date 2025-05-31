import enum

from sqlmodel import Field, SQLModel


class LobbyStatusEnum(enum.Enum):
    CREATED = "created"
    WAITING = "waiting"
    BUSY = "busy"
    ENDED = "ended"


class LobbyStatus(SQLModel, table=True):

    status: str = Field(primary_key=True)
