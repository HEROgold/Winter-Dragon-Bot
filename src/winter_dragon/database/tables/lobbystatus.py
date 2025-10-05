import enum


class LobbyStatus(enum.Enum):
    CREATED = "created"
    WAITING = "waiting"
    BUSY = "busy"
    ENDED = "ended"
