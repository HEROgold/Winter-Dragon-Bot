
from enum import Enum, auto


class ChannelTypes(Enum):
    UNKNOWN = auto()
    STATS = auto()
    LOGS = auto()
    TICKETS = auto()
    TEAM_VOICE = auto()
    TEAM_CATEGORY = auto()
    TEAM_LOBBY = auto()
