"""Module containing channel types for the database."""
from enum import Enum, auto


class ChannelTypes(Enum):
    """Enum containing available channel types for the database."""

    UNKNOWN = auto()
    STATS = auto()
    LOGS = auto()
    TICKETS = auto()
    TEAM_VOICE = auto()
    TEAM_CATEGORY = auto()
    TEAM_LOBBY = auto()
