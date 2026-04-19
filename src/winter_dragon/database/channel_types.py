"""Module containing tags for the database."""

from __future__ import annotations

from enum import Enum, auto


class Tags(Enum):
    """Enum containing available tags for the database."""

    UNKNOWN = auto()
    STATS = auto()
    LOGS = auto()
    TICKETS = auto()
    TEAM_VOICE = auto()
    TEAM_CATEGORY = auto()
    TEAM_LOBBY = auto()
