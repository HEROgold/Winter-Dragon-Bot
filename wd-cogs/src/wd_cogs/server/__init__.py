"""Package for server cogs."""

from .announcement import Announce
from .auto_assign import AutoAssign
from .purge import Purge
from .stats import Stats
from .sync_ban import SyncedBans
from .welcome import Welcome


__all__ = [
    "Announce",
    "AutoAssign",
    "Purge",
    "Stats",
    "SyncedBans",
    "Welcome",
]
