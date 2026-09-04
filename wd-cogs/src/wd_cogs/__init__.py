"""Package for Winter Dragon bot Extensions."""
from __future__ import annotations

lazy from .bot_extension import (
    BotActivity,
    BotControl,
    BotMetrics,
    CogEvents,
    CommandManager,
    Prometheus,
    Sync,
)
lazy from .games import (
    Games,
    Hangman,
    LeagueOfLegends,
    Love,
)
lazy from .server import (
    Announce,
    AutoAssign,
    Purge,
    Stats,
    SyncedBans,
    Welcome,
)
lazy from .tournament import (
    Tournament,
)
lazy from .user import (
    Fuel,
    Reminder,
)
lazy from .utility import (
    Invite,
    Team,
    Uptime,
)


__all__ = [
    # server
    "Announce",
    "AutoAssign",
    # bot_extension
    "BotActivity",
    "BotControl",
    "BotMetrics",
    "CogEvents",
    "CommandManager",
    # user
    "Fuel",
    # games
    "Games",
    "Hangman",
    # utility
    "Invite",
    "LeagueOfLegends",
    "Love",
    "Prometheus",
    "Purge",
    "Reminder",
    "Stats",
    "Sync",
    "SyncedBans",
    "Team",
    # tournament
    "Tournament",
    "Uptime",
    "Welcome",
]
