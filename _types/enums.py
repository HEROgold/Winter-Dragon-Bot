
from enum import Enum, auto


class ChannelTypes(Enum):
    TEXT = auto()
    DM = auto()
    VOICE = auto()
    GROUP_DM = auto()
    CATEGORY = auto()
    NEWS = auto()
    STORE = auto()
    UNKNOWN = auto()
    STATS = auto()
