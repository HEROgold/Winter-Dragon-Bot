import enum

from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel


# TODO: Link the Enum to the LobbyStatus table

class LobbyStatusEnum(enum.Enum):
    CREATED = "created"
    WAITING = "waiting"
    BUSY = "busy"
    ENDED = "ended"


class LobbyStatus(SQLModel, table=True):

    status: LobbyStatusEnum = Field(default=LobbyStatusEnum.CREATED)
