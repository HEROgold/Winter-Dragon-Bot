"""Package for Winter Dragon bot Extensions."""

from .bot_extension import (
    BotActivity,
    BotControl,
    BotMetrics,
    CogEvents,
    CommandManager,
    Prometheus,
    Sync,
)
from .games import (
    Games,
    Hangman,
    LeagueOfLegends,
    Love,
)
from .server import (
    Announce,
    AutoAssign,
    Purge,
    Stats,
    SyncedBans,
    Welcome,
)
from .tournament import (
    Tournament,
)
from .user import (
    Fuel,
    Reminder,
)
from .utility import (
    Invite,
    Team,
    Uptime,
)


__all__ = [
    # bot_extension
    "BotActivity",
    "BotControl",
    "BotMetrics",
    "CogEvents",
    "CommandManager",
    "Prometheus",
    "Sync",
    # games
    "Games",
    "Hangman",
    "LeagueOfLegends",
    "Love",
    # server
    "Announce",
    "AutoAssign",
    "Purge",
    "Stats",
    "SyncedBans",
    "Welcome",
    # tournament
    "Tournament",
    # user
    "Fuel",
    "Reminder",
    # utility
    "Invite",
    "Team",
    "Uptime",
]
